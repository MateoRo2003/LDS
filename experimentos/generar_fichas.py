"""
Genera UNA imagen individual por palabra (no un contact sheet), con los
landmarks dibujados, para armar una ficha de referencia (imagen +
significado) por cada seña del vocabulario actual.

Uso:
    python generar_fichas.py colores
    python generar_fichas.py palabras
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import cv2
import mediapipe as mp

import config
from landmarks import crear_landmarker, dibujar_landmarks

ANCHO, ALTO = 480, 360


def frame_de_muestra(ruta_video):
    landmarker = crear_landmarker()
    cap = cv2.VideoCapture(ruta_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    ms_por_frame = 1000.0 / fps
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    objetivo = max(total // 2, 0)

    frame_elegido = None
    timestamp_ms = 0
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = landmarker.detect_for_video(mp_image, int(timestamp_ms))
        timestamp_ms += ms_por_frame
        if i == objetivo:
            dibujar_landmarks(frame, resultado)
            frame_elegido = frame.copy()
        i += 1

    cap.release()
    landmarker.close()
    return frame_elegido


def generar(categoria):
    vocab = config.vocabulario(categoria)
    salida_dir = os.path.join(os.path.dirname(__file__), "fichas")
    os.makedirs(salida_dir, exist_ok=True)

    for carpeta in vocab:
        ruta_carpeta = os.path.join(config.CARPETA_DATASET_LSA64, carpeta)
        if not os.path.isdir(ruta_carpeta):
            continue
        archivos = sorted(f for f in os.listdir(ruta_carpeta) if f.lower().endswith(".mp4"))
        if not archivos:
            continue

        ruta_video = os.path.join(ruta_carpeta, archivos[0])
        print(f"Procesando {carpeta}...")
        frame = frame_de_muestra(ruta_video)
        if frame is None:
            continue

        frame = cv2.resize(frame, (ANCHO, ALTO))
        nombre_salida = os.path.join(salida_dir, f"{categoria}_{config.palabra_legible(carpeta)}.jpg")
        cv2.imwrite(nombre_salida, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    print(f"\nListo, fichas en {salida_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_fichas.py <categoria>")
        sys.exit(1)
    generar(sys.argv[1])
