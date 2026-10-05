"""
Corre MediaPipe (manos + cuerpo) sobre los videos que necesita una
categoria y guarda los landmarks crudos de cada clip en
datos/procesado/crudo/<seña>/<clip>.npz.

Extrae dos grupos de videos:
- todos los clips de las señas de la categoria;
- una repeticion por persona de las DEMAS señas de LSA64, que el
  entrenamiento usa como ejemplos de "esto no es de la categoria".

Los clips ya extraidos se saltean, asi que volver a correrlo (o correrlo
para otra categoria) solo procesa lo que falta.

Uso:
    python extraer_landmarks.py --categoria colores
"""
import argparse
import os
import re
from multiprocessing import Pool

import cv2
import numpy as np
import mediapipe as mp

import config
from landmarks import crear_landmarker, crear_pose, crudo_de_resultados


def partes_de_nombre(nombre_archivo):
    # "051_005_003.mp4" -> (persona 5, repeticion 3)
    m = re.search(r"_(\d{3})_(\d{3})\.\w+$", nombre_archivo)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def ruta_crudo(carpeta_palabra, nombre_video):
    return os.path.join(config.CARPETA_CRUDO, carpeta_palabra, os.path.splitext(nombre_video)[0] + ".npz")


def clips_de_categoria(categoria):
    """Lista de (carpeta_palabra, nombre_video) que necesita la categoria."""
    vocab = config.vocabulario(categoria)
    # En las computadoras que no tienen los videos de LSA64 (pesan 1.5GB)
    # alcanza con los landmarks ya extraidos, que es lo que se reparte.
    hay_videos = os.path.isdir(config.CARPETA_DATASET_LSA64)
    base = config.CARPETA_DATASET_LSA64 if hay_videos else config.CARPETA_CRUDO
    clips = []
    for carpeta in sorted(os.listdir(base)):
        ruta_carpeta = os.path.join(base, carpeta)
        if not os.path.isdir(ruta_carpeta):
            continue
        for nombre in sorted(os.listdir(ruta_carpeta)):
            if not hay_videos and nombre.endswith(".npz"):
                nombre = nombre[:-4] + ".mp4"
            if not nombre.lower().endswith(".mp4"):
                continue
            if carpeta in vocab or partes_de_nombre(nombre)[1] == config.REPETICION_NEGATIVOS:
                clips.append((carpeta, nombre))
    return clips


def extraer_de_video(clip):
    carpeta_palabra, nombre = clip
    salida = ruta_crudo(carpeta_palabra, nombre)
    if os.path.exists(salida):
        return False

    # Detectores nuevos por video: en modo VIDEO, mediapipe exige
    # timestamps estrictamente crecientes DENTRO de la misma instancia,
    # y ademas arrastra estado de tracking entre frames — reusarlos
    # entre videos distintos mezclaria ambas cosas.
    landmarker = crear_landmarker()
    pose = crear_pose()

    cap = cv2.VideoCapture(os.path.join(config.CARPETA_DATASET_LSA64, carpeta_palabra, nombre))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    paso = max(1, round(fps / config.FPS_OBJETIVO))
    aspecto = cap.get(cv2.CAP_PROP_FRAME_WIDTH) / cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    frames = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % paso == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(i * 1000.0 / fps)
            frames.append(crudo_de_resultados(
                landmarker.detect_for_video(mp_image, timestamp_ms),
                pose.detect_for_video(mp_image, timestamp_ms),
            ))
        i += 1

    cap.release()
    landmarker.close()
    pose.close()

    manos, presente, cuerpo, cuerpo_ok = zip(*frames)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    np.savez_compressed(
        salida,
        manos=np.array(manos), presente=np.array(presente),
        cuerpo=np.array(cuerpo), cuerpo_ok=np.array(cuerpo_ok),
        aspecto=aspecto,
    )
    return True


def main(categoria, procesos):
    if not config.vocabulario(categoria):
        raise SystemExit(f"La categoria '{categoria}' todavia no tiene señas cargadas en config.CATEGORIAS.")

    # bajarlos aca y no en cada proceso, para que no se pisen entre si
    config.asegurar_modelo_landmarker()
    config.asegurar_modelo_pose()

    clips = clips_de_categoria(categoria)
    pendientes = [c for c in clips if not os.path.exists(ruta_crudo(*c))]
    print(f"Categoria '{categoria}': {len(clips)} clips, {len(pendientes)} por extraer")

    with Pool(procesos) as pool:
        for n, _ in enumerate(pool.imap_unordered(extraer_de_video, pendientes), 1):
            if n % 20 == 0 or n == len(pendientes):
                print(f"  {n}/{len(pendientes)}", flush=True)

    print(f"\nLandmarks guardados en {config.CARPETA_CRUDO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", required=True, help="Nombre de categoria en config.CATEGORIAS")
    parser.add_argument("--procesos", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                        help="Cuantos videos procesar en paralelo")
    args = parser.parse_args()
    main(args.categoria, args.procesos)
