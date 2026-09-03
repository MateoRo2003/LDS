"""
App de escritorio: reconocimiento de señas en vivo por webcam, para
UNA categoria a la vez (ej. solo colores, solo la lista de prueba).

- Dibuja el esqueleto de manos de MediaPipe en pantalla en tiempo real
  (el efecto "tecnologico" del que hablamos para la expo).
- Junta una ventana deslizante de frames y, cuando se llena, corre el
  modelo entrenado PARA ESA CATEGORIA y muestra la palabra + confianza.
- Si la confianza no supera UMBRAL_CONFIANZA, muestra "..." en vez de
  arriesgar una palabra incorrecta.

Uso:
    python reconocer_en_vivo.py --categoria colores
    python reconocer_en_vivo.py --categoria prueba   (default)
"""
import argparse
import json
import os
import time
from collections import deque

import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf

import config
from landmarks import crear_landmarker, features_de_resultado, dibujar_landmarks, resamplear_secuencia

UMBRAL_CONFIANZA = 0.6
FRAMES_ENTRE_PREDICCIONES = 5  # no hace falta predecir en cada frame


def cargar_modelo(categoria):
    ruta_modelo = config.ruta_modelo(categoria)
    ruta_etiquetas = config.ruta_etiquetas(categoria)
    if not os.path.exists(ruta_modelo):
        raise FileNotFoundError(
            f"No existe {ruta_modelo} — corré primero:\n"
            f"  python extraer_landmarks.py --categoria {categoria}\n"
            f"  python entrenar_modelo.py --categoria {categoria}"
        )
    modelo = tf.keras.models.load_model(ruta_modelo)
    with open(ruta_etiquetas, encoding="utf-8") as f:
        meta = json.load(f)
    clases = meta["clases"]
    media = np.array(meta["media"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)
    return modelo, clases, media, std


def dibujar_prediccion(frame, categoria, texto, confianza):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 70), (w, h), (20, 20, 20), -1)
    color = (80, 220, 130) if confianza >= UMBRAL_CONFIANZA else (150, 150, 150)
    cv2.putText(frame, texto, (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2, cv2.LINE_AA)
    if confianza > 0:
        cv2.putText(frame, f"{confianza*100:.0f}%", (w - 120, h - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"modo: {categoria}", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)


def main(categoria):
    modelo, clases, media, std = cargar_modelo(categoria)
    landmarker = crear_landmarker()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No pude abrir la webcam.")
        return

    buffer = deque(maxlen=config.LONGITUD_SECUENCIA * 2)  # margen para resamplear
    inicio = time.time()
    frame_i = 0
    ultima_palabra = "..."
    ultima_confianza = 0.0

    print(f"Reconociendo en vivo (categoria: {categoria}). Apretá 'q' para salir.")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_i += 1

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - inicio) * 1000)
        resultado = landmarker.detect_for_video(mp_image, timestamp_ms)

        dibujar_landmarks(frame, resultado)
        buffer.append(features_de_resultado(resultado))

        if frame_i % FRAMES_ENTRE_PREDICCIONES == 0 and len(buffer) >= config.LONGITUD_SECUENCIA:
            secuencia = resamplear_secuencia(list(buffer), config.LONGITUD_SECUENCIA)
            secuencia_norm = (secuencia - media[0]) / std[0]
            entrada = secuencia_norm[np.newaxis, ...]  # (1, frames, features)

            probs = modelo.predict(entrada, verbose=0)[0]
            idx = int(np.argmax(probs))
            ultima_confianza = float(probs[idx])
            ultima_palabra = config.palabra_es(clases[idx]) if ultima_confianza >= UMBRAL_CONFIANZA else "..."

        dibujar_prediccion(frame, categoria, ultima_palabra, ultima_confianza)
        # Titulo sin tildes/rayas: cv2.imshow rompe la codificacion de
        # caracteres no-ASCII en la barra de titulo en Windows.
        cv2.imshow("Reconocimiento de senas LSA (q para salir)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", default="prueba", help="Nombre de categoria en config.CATEGORIAS")
    args = parser.parse_args()
    main(args.categoria)
