"""
Motor del reconocimiento en vivo. No tiene interfaz: app.py lo arranca
y le muestra al navegador lo que este motor va publicando (la imagen de
la camara y el estado).

Dos piezas:

- SeguidorDeSena: la logica pura. Recibe los landmarks de cada frame y
  decide que seña se esta haciendo. No sabe nada de camaras, asi que
  experimentos/smoke_test_reconocimiento.py la puede probar con clips.
- Reconocedor: el hilo que lee la webcam, corre MediaPipe y alimenta al
  seguidor de la categoria elegida. La camara queda abierta todo el
  tiempo; cambiar de categoria solo cambia el modelo.
"""
import json
import os
import threading
import time
from collections import deque

import numpy as np

import config
import estaticas
from landmarks import features_de_secuencia, resamplear_secuencia

# Una seña de LSA64 dura entre 1 y 2 segundos y nadie la hace siempre a
# la misma velocidad: se prueba con varias ventanas hacia atras y se
# usa la que el modelo ve mas clara.
VENTANAS_S = (1.0, 1.5, 2.2)
MINIMO_S = 0.6                 # con menos que esto no hay seña posible
SIN_MANO_S = 0.7               # tanto tiempo sin mano = la seña termino
FRAMES_ENTRE_PREDICCIONES = 4  # no hace falta predecir en cada frame
SUAVIZADO = 3                  # se promedian las ultimas N predicciones
RETENER_S = 2.0                # cuanto queda en pantalla la ultima seña


class SeguidorDeSena:
    def __init__(self, modelo, clases, aspecto):
        self.modelo = modelo
        self.clases = clases
        self.nada = clases.index(config.CLASE_NADA)
        self.aspecto = aspecto
        self.buffer = deque()
        self.recientes = deque(maxlen=SUAVIZADO)
        self.ultima_mano_t = None
        self.frames = 0
        self.hay_mano = False
        self.hay_cuerpo = False
        self.confianza = 0.0       # de la prediccion actual, sea cual sea
        self.detectada = None      # (indice de clase, confianza, t) vigente
        self.candidata = None      # seña vista en la prediccion anterior
        self.nueva = False         # True solo en el frame en que aparece una seña

    def procesar(self, t, crudo, umbral):
        manos, presente, cuerpo, cuerpo_ok = crudo
        self.nueva = False
        self.hay_mano = bool(presente.any())
        self.hay_cuerpo = bool(cuerpo_ok)
        self.frames += 1

        if self.hay_mano:
            self.ultima_mano_t = t
        elif self.ultima_mano_t is None or t - self.ultima_mano_t > SIN_MANO_S:
            # sin manos: se termina la seña y se empieza de cero
            self.buffer.clear()
            self.recientes.clear()
            self.candidata = None
            self.confianza = 0.0
            self.ultima_mano_t = None
            self._vencer(t)
            return

        self.buffer.append((t, manos, presente, cuerpo, cuerpo_ok))
        while t - self.buffer[0][0] > VENTANAS_S[-1]:
            self.buffer.popleft()

        if self.frames % FRAMES_ENTRE_PREDICCIONES == 0 and t - self.buffer[0][0] >= MINIMO_S:
            self._predecir(t, umbral)
        self._vencer(t)

    def _vencer(self, t):
        if self.detectada and t - self.detectada[2] > RETENER_S:
            self.detectada = None

    def _predecir(self, t, umbral):
        tiempos = np.array([f[0] for f in self.buffer])
        entradas = []
        for ventana in VENTANAS_S:
            desde = int(np.searchsorted(tiempos, t - ventana))
            _, manos, presente, cuerpo, cuerpo_ok = zip(*list(self.buffer)[desde:])
            feats = features_de_secuencia(manos, presente, cuerpo, cuerpo_ok, self.aspecto)
            if feats is None:
                return
            entradas.append(resamplear_secuencia(feats))
            if desde == 0:
                break  # las ventanas mas largas serian esta misma

        probs = self.modelo(np.array(entradas), training=False).numpy()
        senas = np.delete(probs, self.nada, axis=1)
        self.recientes.append(probs[senas.max(axis=1).argmax()])

        promedio = np.mean(self.recientes, axis=0)
        idx = int(promedio.argmax())
        self.confianza = float(promedio[idx]) if idx != self.nada else 0.0
        acepta = idx != self.nada and self.confianza >= umbral
        # Una seña nueva tiene que sostenerse dos predicciones seguidas:
        # filtra los falsos de un instante, tipicos de cuando la mano
        # baja despues de terminar otra seña.
        if acepta and (idx == self.candidata or (self.detectada and self.detectada[0] == idx)):
            self.nueva = self.detectada is None or self.detectada[0] != idx
            self.detectada = (idx, self.confianza, t)
        self.candidata = idx if acepta else None


class Reconocedor:
    def __init__(self):
        self.ajustes = {"umbral": 0.6, "esqueleto": True, "espejo": True}
        self.categoria = None
        self.camara = 0            # numero de camara que usa OpenCV
        self.camaras = []          # las que se encontraron conectadas
        self.buscar_camaras = True
        self.historial = []
        self.hay_frame = threading.Condition()
        self.jpeg = None
        self._estado = {"fase": "cargando", "mensaje": "Cargando el reconocimiento…"}
        self._modelos = {}
        self._seguidor = None
        self._seguidor_categoria = None
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, daemon=True)

    def iniciar(self):
        self._hilo.start()

    def detener(self):
        self._activo = False
        self._hilo.join(timeout=5)

    def elegir_categoria(self, categoria):
        if categoria is not None and categoria not in categorias_disponibles():
            raise ValueError(f"La categoria '{categoria}' no tiene modelo entrenado")
        self.categoria = categoria

    def elegir_camara(self, camara):
        if camara not in self.camaras:
            raise ValueError(f"No hay ninguna camara {camara}")
        self.camara = camara

    def estado(self):
        return {**self._estado, "categoria": self.categoria, "ajustes": self.ajustes,
                "camara": self.camara, "camaras": self.camaras,
                "historial": self.historial[-30:]}

    def _cargar_modelo(self, categoria):
        if categoria not in self._modelos:
            import tensorflow as tf

            modelo = tf.keras.models.load_model(config.ruta_modelo(categoria))
            with open(config.ruta_etiquetas(categoria), encoding="utf-8") as f:
                etiquetas = json.load(f)
            # la primera llamada es lenta: que no le toque a la primera seña
            modelo(np.zeros((1, *modelo.input_shape[1:]), dtype=np.float32))
            self._modelos[categoria] = (modelo, etiquetas["clases"], etiquetas.get("tipo") == "estatica")
        return self._modelos[categoria]

    def _publicar(self, jpeg):
        with self.hay_frame:
            self.jpeg = jpeg
            self.hay_frame.notify_all()

    def _bucle(self):
        try:
            self._leer_camara()
        except Exception as e:
            self._estado = {"fase": "error", "mensaje": f"El reconocimiento se detuvo por un error: {e}"}
            raise

    def _leer_camara(self):
        # imports pesados aca adentro: asi la ventana abre enseguida y
        # muestra "cargando" mientras tanto
        import cv2
        import mediapipe as mp

        from landmarks import crear_landmarker, crear_pose, crudo_de_resultados, dibujar_landmarks

        landmarker = crear_landmarker()
        pose = crear_pose()
        for categoria in categorias_disponibles():
            self._cargar_modelo(categoria)

        cap = None
        camara_abierta = None
        inicio = time.monotonic()
        ultimo_ms = -1

        while self._activo:
            if self.buscar_camaras or camara_abierta != self.camara:
                if cap is not None:
                    cap.release()
                    cap = None
                if self.buscar_camaras:
                    self.camaras = self._camaras_conectadas(cv2)
                    if self.camaras and self.camara not in self.camaras:
                        self.camara = self.camaras[0]
                    self.buscar_camaras = False
                camara_abierta = self.camara
                self._seguidor_categoria = None  # otra camara: se empieza de cero
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(self.camara)
                # sin pedirlo, OpenCV abre cualquier camara en 640x480
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            ok, frame = cap.read() if cap.isOpened() else (False, None)
            if not ok:
                self._estado = {"fase": "sin_camara",
                                "mensaje": "No pude abrir la cámara. Revisá que esté conectada y que no la esté usando otro programa."}
                cap.release()
                cap = None
                time.sleep(2)
                continue

            t = time.monotonic() - inicio
            ultimo_ms = max(ultimo_ms + 1, int(t * 1000))  # mediapipe los exige crecientes
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            resultado = landmarker.detect_for_video(mp_image, ultimo_ms)
            crudo = crudo_de_resultados(resultado, pose.detect_for_video(mp_image, ultimo_ms))

            self._estado = self._reconocer(t, crudo, frame.shape[1] / frame.shape[0])

            if self.ajustes["esqueleto"]:
                dibujar_landmarks(frame, resultado)
            if self.ajustes["espejo"]:
                frame = cv2.flip(frame, 1)
            self._publicar(cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes())

        if cap is not None:
            cap.release()
        landmarker.close()
        pose.close()

    @staticmethod
    def _camaras_conectadas(cv2):
        # OpenCV no sabe listar camaras: se prueba abrir una por una. Los
        # numeros son corridos, asi que la primera que falla es el final.
        encontradas = []
        for i in range(6):
            cap = cv2.VideoCapture(i)
            abre = cap.isOpened() and cap.read()[0]
            cap.release()
            if not abre:
                break
            encontradas.append(i)
        return encontradas

    def _reconocer(self, t, crudo, aspecto):
        categoria = self.categoria
        estado = {"fase": "listo", "mano": bool(crudo[1].any()), "cuerpo": bool(crudo[3]),
                  "palabra": None, "confianza": 0.0}
        if categoria is None:
            self._seguidor = self._seguidor_categoria = None
            return estado

        if self._seguidor_categoria != categoria:
            modelo, clases, estatica = self._cargar_modelo(categoria)
            seguidor = estaticas.SeguidorEstatico if estatica else SeguidorDeSena
            self._seguidor = seguidor(modelo, clases, aspecto)
            self._seguidor_categoria = categoria

        seguidor = self._seguidor
        seguidor.procesar(t, crudo, self.ajustes["umbral"])
        estado["confianza"] = seguidor.confianza
        if seguidor.detectada:
            idx, confianza, _ = seguidor.detectada
            estado["palabra"] = config.palabra_es(seguidor.clases[idx])
            estado["confianza"] = confianza
            if seguidor.nueva:
                self.historial.append({
                    "id": len(self.historial) + 1,
                    "palabra": estado["palabra"],
                    "tipo": config.INFO_CATEGORIAS[categoria][1],
                    "confianza": confianza,
                    "hora": time.time(),
                })
        return estado


def categorias_disponibles():
    return [c for c in config.CATEGORIAS if os.path.exists(config.ruta_modelo(c))]


def _senas_aprendidas(categoria):
    """Las señas que sabe el modelo de una categoria estatica."""
    with open(config.ruta_etiquetas(categoria), encoding="utf-8") as f:
        return json.load(f)["clases"]


def info_categorias():
    """Lo que la interfaz necesita saber de cada categoria."""
    disponibles = categorias_disponibles()
    info = []
    for c, senas in config.CATEGORIAS.items():
        estatica = c in config.SENAS_ESTATICAS
        if estatica:
            senas = _senas_aprendidas(c) if c in disponibles else []
        info.append({
            "id": c,
            "titulo": config.INFO_CATEGORIAS[c][0],
            "tipo": config.INFO_CATEGORIAS[c][1],
            "disponible": c in disponibles,
            "estatica": estatica,
            "senas": [config.palabra_es(s) for s in senas],
        })
    return info
