"""
Recorre las carpetas de una categoria (config.CATEGORIAS) dentro de
datos/externos/lsa64_por_palabra/, corre MediaPipe sobre cada video, y
guarda un dataset de secuencias de landmarks listo para entrenar en
datos/procesado/dataset_<categoria>.npz.

Uso:
    python extraer_landmarks.py --categoria colores
    python extraer_landmarks.py --categoria prueba   (default)
"""
import argparse
import os
import cv2
import numpy as np
import mediapipe as mp

import config
from landmarks import crear_landmarker, features_de_resultado, resamplear_secuencia


def extraer_de_video(ruta_video):
    # Un landmarker nuevo por video: en modo VIDEO, mediapipe exige
    # timestamps estrictamente crecientes DENTRO de la misma instancia,
    # y ademas arrastra estado de tracking entre frames — reusar uno
    # solo entre videos distintos mezclaria ambas cosas.
    landmarker = crear_landmarker()

    cap = cv2.VideoCapture(ruta_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    ms_por_frame = 1000.0 / fps

    frames_features = []
    timestamp_ms = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = landmarker.detect_for_video(mp_image, int(timestamp_ms))
        timestamp_ms += ms_por_frame
        frames_features.append(features_de_resultado(resultado))

    cap.release()
    landmarker.close()
    return resamplear_secuencia(frames_features)


def main(categoria):
    vocab = config.vocabulario(categoria)
    X, y, nombres_archivo = [], [], []

    for idx_clase, carpeta_palabra in enumerate(vocab):
        ruta_carpeta = os.path.join(config.CARPETA_DATASET_LSA64, carpeta_palabra)
        if not os.path.isdir(ruta_carpeta):
            print(f"[AVISO] No existe la carpeta: {ruta_carpeta} — la salteo")
            continue

        archivos = sorted(f for f in os.listdir(ruta_carpeta) if f.lower().endswith(".mp4"))
        print(f"[{idx_clase}] {carpeta_palabra}: {len(archivos)} videos")

        for nombre in archivos:
            ruta_video = os.path.join(ruta_carpeta, nombre)
            secuencia = extraer_de_video(ruta_video)
            X.append(secuencia)
            y.append(idx_clase)
            nombres_archivo.append(f"{carpeta_palabra}/{nombre}")

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)

    ruta_salida = config.ruta_dataset(categoria)
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    np.savez_compressed(
        ruta_salida,
        X=X,
        y=y,
        clases=np.array(vocab),
        nombres_archivo=np.array(nombres_archivo),
    )

    print(f"\nDataset guardado en {ruta_salida}")
    print(f"X shape: {X.shape}  (videos, frames, features)")
    print(f"y shape: {y.shape}")
    print(f"Clases: {list(vocab)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", default="prueba", help="Nombre de categoria en config.CATEGORIAS")
    args = parser.parse_args()
    main(args.categoria)
