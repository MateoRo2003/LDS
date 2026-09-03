"""
Prueba rapida: ¿MediaPipe detecta una mano con guante de color?

Antes de invertir tiempo convirtiendo video con guante a "piel", probemos
la pregunta real: ¿el detector de manos reconoce un guante puesto, sea en
un clip ya grabado (ej. de LSA64) o frente a la propia webcam?

Instalar dependencias (una sola vez):
    pip install mediapipe opencv-python

Uso — modo camara en vivo (no necesita ningun archivo):
    python probar_deteccion_guante.py
    python probar_deteccion_guante.py --segundos 15

    Se abre la webcam, se ponen el guante, y se mira en pantalla si
    aparecen los puntos sobre la mano. Se corta solo despues de N
    segundos (15 por defecto) o apretando "q".

Uso — modo archivo (para un video ya grabado, ej. un clip de LSA64):
    python probar_deteccion_guante.py ruta/al/video.mp4

Que hace:
    - Corre el HandLandmarker de MediaPipe (API nueva "Tasks", la vieja
      mp.solutions.hands ya no existe desde mediapipe 1.0) frame a frame.
    - Cuenta en que porcentaje de frames detecto una mano.
    - Muestra (camara) o guarda (archivo) el video con los puntos
      dibujados encima, para confirmar a ojo si el tracking queda bien
      puesto o no — el % solo no alcanza.

Nota sobre versiones: si alguien del equipo tiene Python 3.9-3.12, puede
llegar a instalarsele una version vieja de mediapipe (<1.0) que todavia
usa la API clasica (mp.solutions.hands) de los tutoriales viejos de
internet. Este script funciona con la API nueva (Tasks), que es la que
instala "pip install mediapipe" en Python 3.13 y en general de ahora en
mas. Si el pip install les trae una version vieja, actualizar con
"pip install --upgrade mediapipe" antes de correr esto.
"""
import argparse
import os
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def asegurar_modelo():
    if not os.path.exists(MODEL_PATH):
        print("Bajando el modelo de deteccion de manos (una sola vez, ~8MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Listo.\n")


def crear_landmarker():
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=2,
        running_mode=vision.RunningMode.VIDEO,
        min_hand_detection_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def dibujar(frame_bgr, resultado):
    for hand_landmarks in resultado.hand_landmarks:
        vision.drawing_utils.draw_landmarks(
            frame_bgr,
            hand_landmarks,
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            vision.drawing_styles.get_default_hand_landmarks_style(),
            vision.drawing_styles.get_default_hand_connections_style(),
        )


def _reportar(total_frames, frames_con_mano):
    pct = (frames_con_mano / total_frames * 100) if total_frames else 0
    print(f"\nFrames totales: {total_frames}")
    print(f"Frames con mano detectada: {frames_con_mano} ({pct:.1f}%)")

    if pct < 50:
        print("\n-> MediaPipe falla en la mayoria de los frames. El guante tal cual no sirve para alimentar este pipeline.")
    elif pct < 90:
        print("\n-> Detecta parcialmente. Revisen a ojo si los puntos quedan bien puestos aunque 'detecte' — eso importa mas que el %.")
    else:
        print("\n-> Detecta casi siempre. Revisen igual a ojo que los puntos caigan bien sobre los dedos, no solo que 'hay deteccion'.")
    return pct


def probar_archivo(video_path, guardar_video_anotado=True):
    asegurar_modelo()
    landmarker = crear_landmarker()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"No pude abrir el video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ms_por_frame = 1000.0 / fps

    writer = None
    salida = None
    if guardar_video_anotado:
        nombre = os.path.basename(video_path)
        salida = f"deteccion_{nombre}"
        writer = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    total_frames = 0
    frames_con_mano = 0
    timestamp_ms = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        total_frames += 1

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = landmarker.detect_for_video(mp_image, int(timestamp_ms))
        timestamp_ms += ms_por_frame

        if resultado.hand_landmarks:
            frames_con_mano += 1
            dibujar(frame, resultado)

        if writer:
            writer.write(frame)

    cap.release()
    if writer:
        writer.release()
    landmarker.close()

    if salida:
        print(f"Video anotado guardado como: {salida}  (miralo para confirmar si los puntos quedan bien puestos, no solo el %)")
    print(f"\nVideo: {video_path}")
    _reportar(total_frames, frames_con_mano)


def probar_camara(segundos=15):
    asegurar_modelo()
    landmarker = crear_landmarker()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No pude abrir la webcam (dispositivo 0). Probá cerrar otras apps que la esten usando.")
        return

    total_frames = 0
    frames_con_mano = 0
    inicio = time.time()

    print(f"Camara abierta. Poné el guante frente a la camara. Se corta solo a los {segundos}s (o apretando 'q').")

    while (time.time() - inicio) < segundos:
        ok, frame = cap.read()
        if not ok:
            break
        total_frames += 1

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - inicio) * 1000)
        resultado = landmarker.detect_for_video(mp_image, timestamp_ms)

        if resultado.hand_landmarks:
            frames_con_mano += 1
            dibujar(frame, resultado)

        cv2.imshow("Prueba deteccion con guante (q para cortar)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    _reportar(total_frames, frames_con_mano)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba si MediaPipe detecta una mano con guante.")
    parser.add_argument("video", nargs="?", default=None, help="Ruta a un video (si no se pasa, usa la webcam en vivo)")
    parser.add_argument("--segundos", type=int, default=15, help="Duracion de la prueba en modo camara (default 15)")
    args = parser.parse_args()

    if args.video:
        probar_archivo(args.video)
    else:
        probar_camara(args.segundos)
