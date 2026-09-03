"""
Prueba de humo: corre el MISMO codigo que usa reconocer_en_vivo.py
(cargar_modelo, features_de_resultado, resamplear_secuencia) pero
alimentado con un video en vez de la webcam — para verificar que la
app en vivo no tiene bugs sin necesitar una camara fisica.

Uso:
    python smoke_test_reconocimiento.py ruta/al/video.mp4 palabra_esperada
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import cv2
import numpy as np
import mediapipe as mp

import config
from landmarks import crear_landmarker, features_de_resultado, resamplear_secuencia
from reconocer_en_vivo import cargar_modelo


def main(video_path, palabra_esperada):
    modelo, clases, media, std = cargar_modelo()
    landmarker = crear_landmarker()

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    ms_por_frame = 1000.0 / fps

    buffer = []
    timestamp_ms = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = landmarker.detect_for_video(mp_image, int(timestamp_ms))
        timestamp_ms += ms_por_frame
        buffer.append(features_de_resultado(resultado))

    cap.release()
    landmarker.close()

    secuencia = resamplear_secuencia(buffer, config.LONGITUD_SECUENCIA)
    secuencia_norm = (secuencia - media[0]) / std[0]
    entrada = secuencia_norm[np.newaxis, ...]

    probs = modelo.predict(entrada, verbose=0)[0]
    idx = int(np.argmax(probs))
    predicha = config.palabra_legible(clases[idx])
    confianza = float(probs[idx])

    print(f"\nVideo: {video_path}")
    print(f"Esperada: {palabra_esperada}")
    print(f"Predicha: {predicha} ({confianza*100:.1f}%)")
    print(f"Resultado: {'OK' if predicha == palabra_esperada else 'FALLO'}")

    print("\nTodas las probabilidades:")
    for c, p in sorted(zip(clases, probs), key=lambda x: -x[1]):
        print(f"  {config.palabra_legible(c):10s} {p*100:5.1f}%")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
