"""
Genera UNA imagen (contact sheet) con un frame de muestra por cada
palabra de una categoria, con los landmarks de MediaPipe dibujados
encima — para verificar a simple vista que el sistema esta "mirando"
lo que corresponde en cada palabra.

Uso:
    python generar_muestra_visual.py colores
    python generar_muestra_visual.py palabras
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import cv2
import numpy as np
import mediapipe as mp

import config
from landmarks import crear_landmarker, dibujar_landmarks

MINIATURA_W = 320
MINIATURA_H = 240


def frame_de_muestra(ruta_video):
    landmarker = crear_landmarker()
    cap = cv2.VideoCapture(ruta_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    ms_por_frame = 1000.0 / fps

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    objetivo = max(total // 2, 0)  # frame del medio del clip

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
    miniaturas = []

    for carpeta in vocab:
        ruta_carpeta = os.path.join(config.CARPETA_DATASET_LSA64, carpeta)
        if not os.path.isdir(ruta_carpeta):
            print(f"[AVISO] no existe {ruta_carpeta}, la salteo")
            continue
        archivos = sorted(f for f in os.listdir(ruta_carpeta) if f.lower().endswith(".mp4"))
        if not archivos:
            continue

        ruta_video = os.path.join(ruta_carpeta, archivos[0])
        print(f"Procesando {carpeta} ({archivos[0]})...")
        frame = frame_de_muestra(ruta_video)
        if frame is None:
            continue

        mini = cv2.resize(frame, (MINIATURA_W, MINIATURA_H))
        etiqueta = config.palabra_es(carpeta)
        cv2.rectangle(mini, (0, MINIATURA_H - 30), (MINIATURA_W, MINIATURA_H), (20, 20, 20), -1)
        cv2.putText(mini, etiqueta, (10, MINIATURA_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        miniaturas.append(mini)

    if not miniaturas:
        print("No se genero ninguna miniatura.")
        return

    columnas = 4
    filas = math.ceil(len(miniaturas) / columnas)
    hoja = np.full((filas * MINIATURA_H, columnas * MINIATURA_W, 3), 30, dtype=np.uint8)

    for idx, mini in enumerate(miniaturas):
        fila, col = divmod(idx, columnas)
        y0, x0 = fila * MINIATURA_H, col * MINIATURA_W
        hoja[y0:y0 + MINIATURA_H, x0:x0 + MINIATURA_W] = mini

    salida = os.path.join(os.path.dirname(__file__), f"muestra_visual_{categoria}.png")
    cv2.imwrite(salida, hoja)
    print(f"\nGuardado: {salida}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_muestra_visual.py <categoria>")
        sys.exit(1)
    generar(sys.argv[1])
