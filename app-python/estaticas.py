"""
Señas estaticas (abecedario y numeros): sus muestras, el entrenamiento
de su modelo y el reconocimiento en vivo.

A diferencia de las señas con movimiento (reconocedor.SeguidorDeSena),
aca alcanza con la postura en un instante (forma de las manos y donde
estan respecto de la cara), asi que el modelo es una red chica que mira
un solo frame y se entrena en segundos.

Las letras de LSA que llevan movimiento se reconocen por las posturas
por las que pasan: dos letras con la misma postura y distinto movimiento
se van a confundir.

Las muestras son archivos .npy en CARPETA_ESTATICAS/<categoria>/<seña>/,
uno por video de origen (los arma experimentos/senas_desde_videos.py,
que tambien entrena).

Uso por consola, para volver a entrenar con las muestras que ya hay:
    python estaticas.py --categoria abecedario
"""
import argparse
import json
import os
from collections import deque

import numpy as np

import config
from landmarks import posturas

SOSTENER_S = 0.5   # cuanto hay que mantener la seña para que cuente
RETENER_S = 1.0    # cuanto queda en pantalla despues de soltarla
SUAVIZADO = 8      # frames que se promedian
REFERENCIA = 15    # frames recientes con los que se ubica la cara
EPOCAS = 60
COPIAS = 4         # versiones aumentadas de cada postura


def _carpeta(categoria, sena):
    if sena not in config.SENAS_ESTATICAS[categoria]:
        raise ValueError(f"'{sena}' no es una seña de '{categoria}'")
    return os.path.join(config.CARPETA_ESTATICAS, categoria, sena)


def guardar(categoria, sena, frames_crudos, aspecto, nombre):
    """Guarda las posturas de un tramo de video. -> cuantos frames utiles tenia (0 = no se guardo nada)."""
    feats, con_mano = posturas(frames_crudos, aspecto)
    if feats is None or not con_mano.any():
        return 0
    carpeta = _carpeta(categoria, sena)
    os.makedirs(carpeta, exist_ok=True)
    np.save(os.path.join(carpeta, nombre + ".npy"), feats[con_mano])
    return int(con_mano.sum())


def _aumentar(X, rng):
    """Variantes de cada postura: las manos apenas giradas, mas grandes o
    mas chicas, un poco corridas y con temblor."""
    X = np.repeat(X, COPIAS, axis=0).copy()
    n = len(X)
    hay_otra = X[:, -1:]
    angulo = np.deg2rad(rng.normal(0, 8, (n, 1)))
    escala = rng.uniform(0.9, 1.1, (n, 1, 1))
    for desde in (0, 63 + 6):  # la forma de cada mano
        forma = X[:, desde:desde + 63].reshape(n, 21, 3)
        x, y = forma[..., 0].copy(), forma[..., 1].copy()
        forma[..., 0] = np.cos(angulo) * x - np.sin(angulo) * y
        forma[..., 1] = np.sin(angulo) * x + np.cos(angulo) * y
        forma *= escala
        forma += rng.normal(0, 0.03, forma.shape)
    # poco corrimiento: frente, boca y menton estan a menos de medio
    # ancho de hombros entre si
    lugar = X[:, 63:69].reshape(n, 3, 2)
    lugar *= rng.uniform(0.9, 1.1, (n, 1, 1))
    lugar += rng.normal(0, 0.06, (n, 1, 2))
    X[:, -3:-1] += rng.normal(0, 0.05, (n, 2))
    X[:, 69:-1] *= hay_otra
    return X.astype(np.float32)


def entrenar_red(X, y, cuantas_clases):
    """Red chica que mira una postura. X sin aumentar; aca se generan las variantes."""
    from tensorflow.keras.layers import Dense, Dropout, Input
    from tensorflow.keras.models import Sequential

    rng = np.random.default_rng(0)
    X, y = _aumentar(X, rng), np.repeat(y, COPIAS)
    # que una seña con muchas muestras no tape a las demas
    cuenta = np.bincount(y, minlength=cuantas_clases)
    pesos = {i: float(len(y) / (cuantas_clases * max(c, 1))) for i, c in enumerate(cuenta)}

    modelo = Sequential([
        Input(shape=(X.shape[1],)),
        Dense(128, activation="relu"),
        Dropout(0.3),
        Dense(64, activation="relu"),
        Dense(cuantas_clases, activation="softmax"),
    ])
    modelo.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    modelo.fit(X, y, epochs=EPOCAS, batch_size=64, verbose=0, class_weight=pesos)
    return modelo


def entrenar(categoria):
    """Entrena con las muestras que hay. -> (señas aprendidas, acierto en validacion)"""
    clases, X_train, y_train, X_val, y_val = [], [], [], [], []
    for sena in config.SENAS_ESTATICAS[categoria]:
        carpeta = _carpeta(categoria, sena)
        archivos = sorted(os.listdir(carpeta)) if os.path.isdir(carpeta) else []
        if not archivos:
            continue
        grabaciones = [np.load(os.path.join(carpeta, a)) for a in archivos]
        # Se valida con el final de cada tramo. Es una medida optimista
        # (misma persona, mismo momento): sirve para detectar muestras mal
        # armadas, no para saber como anda con gente nueva; eso lo mide
        # senas_desde_videos.py --evaluar.
        for grabacion in grabaciones:
            corte = max(1, int(len(grabacion) * 0.8))
            X_train.append(grabacion[:corte])
            y_train.append(np.full(corte, len(clases)))
            X_val.append(grabacion[corte:])
            y_val.append(np.full(len(grabacion) - corte, len(clases)))
        clases.append(sena)

    if len(clases) < 2:
        raise ValueError("Hacen falta muestras de al menos 2 señas para entrenar.")

    modelo = entrenar_red(np.concatenate(X_train), np.concatenate(y_train), len(clases))
    acierto = float(modelo.evaluate(np.concatenate(X_val), np.concatenate(y_val), verbose=0)[1])

    os.makedirs(os.path.dirname(config.ruta_modelo(categoria)), exist_ok=True)
    modelo.save(config.ruta_modelo(categoria))
    with open(config.ruta_etiquetas(categoria), "w", encoding="utf-8") as f:
        json.dump({"tipo": "estatica", "clases": clases}, f, ensure_ascii=False, indent=2)
    return clases, acierto


class SeguidorEstatico:
    """Misma interfaz que reconocedor.SeguidorDeSena, para señas sin movimiento."""

    def __init__(self, modelo, clases, aspecto):
        self.modelo = modelo
        self.clases = clases
        self.aspecto = aspecto
        self.frames = deque(maxlen=REFERENCIA)
        self.recientes = deque(maxlen=SUAVIZADO)
        self.candidata = None      # (indice de clase, desde cuando se sostiene)
        self.confianza = 0.0
        self.detectada = None      # (indice de clase, confianza, t) vigente
        self.nueva = False

    def procesar(self, t, crudo, umbral):
        self.nueva = False
        self.frames.append(crudo)
        feats, con_mano = posturas(self.frames, self.aspecto)
        if feats is None or not con_mano[-1]:
            self.recientes.clear()
            self.candidata = None
            self.confianza = 0.0
        else:
            self.recientes.append(self.modelo(feats[-1:], training=False).numpy()[0])
            promedio = np.mean(self.recientes, axis=0)
            idx = int(promedio.argmax())
            self.confianza = float(promedio[idx])
            if self.confianza < umbral:
                self.candidata = None
            else:
                if self.candidata is None or self.candidata[0] != idx:
                    self.candidata = (idx, t)
                sigue = self.detectada is not None and self.detectada[0] == idx
                if sigue or t - self.candidata[1] >= SOSTENER_S:
                    self.nueva = not sigue
                    self.detectada = (idx, self.confianza, t)

        if self.detectada and t - self.detectada[2] > RETENER_S:
            self.detectada = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", required=True, choices=list(config.SENAS_ESTATICAS))
    args = parser.parse_args()
    aprendidas, acierto = entrenar(args.categoria)
    print(f"Señas aprendidas ({len(aprendidas)}): {' '.join(aprendidas)}")
    print(f"Acierto en validacion: {acierto * 100:.0f}%")
