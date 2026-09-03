"""
Funciones compartidas para extraer y dibujar landmarks de mano con
MediaPipe (API nueva "Tasks" — mp.solutions.hands ya no existe desde
mediapipe 1.0). Usado tanto por extraer_landmarks.py (offline, sobre
videos) como por reconocer_en_vivo.py (tiempo real, sobre la webcam).
"""
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

import config

PUNTOS_POR_MANO = 21
COORDS_POR_PUNTO = 3  # x, y, z


def crear_landmarker(running_mode=None):
    config.asegurar_modelo_landmarker()
    modo = running_mode or vision.RunningMode.VIDEO
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=config.RUTA_MODELO_LANDMARKER),
        num_hands=2,
        running_mode=modo,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def features_de_resultado(resultado):
    """
    Convierte un HandLandmarkerResult en un vector fijo de
    FEATURES_POR_FRAME numeros: [mano_izq (21x3), mano_der (21x3)].
    Si una mano no fue detectada, su bloque queda en ceros. Ordenar por
    handedness (no por orden de deteccion) evita que los features salten
    de "mano derecha" a "mano izquierda" entre frames por error del
    tracker, algo que confundiria mucho a la LSTM.
    """
    vec_izq = np.zeros(PUNTOS_POR_MANO * COORDS_POR_PUNTO, dtype=np.float32)
    vec_der = np.zeros(PUNTOS_POR_MANO * COORDS_POR_PUNTO, dtype=np.float32)

    for landmarks, handedness in zip(resultado.hand_landmarks, resultado.handedness):
        etiqueta = handedness[0].category_name  # "Left" o "Right"
        vals = np.array(
            [[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32
        ).flatten()
        if etiqueta == "Left":
            vec_izq = vals
        else:
            vec_der = vals

    return np.concatenate([vec_izq, vec_der])


def dibujar_landmarks(frame_bgr, resultado):
    for hand_landmarks in resultado.hand_landmarks:
        vision.drawing_utils.draw_landmarks(
            frame_bgr,
            hand_landmarks,
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            vision.drawing_styles.get_default_hand_landmarks_style(),
            vision.drawing_styles.get_default_hand_connections_style(),
        )


def resamplear_secuencia(frames_features, longitud=None):
    """
    Estira o comprime una lista de vectores de features (uno por frame)
    a exactamente `longitud` frames, para que todos los clips entren con
    el mismo tamaño al modelo sin importar cuanto duraron originalmente.
    """
    longitud = longitud or config.LONGITUD_SECUENCIA
    total = len(frames_features)
    if total == 0:
        return np.zeros((longitud, config.FEATURES_POR_FRAME), dtype=np.float32)

    indices = np.linspace(0, total - 1, longitud).round().astype(int)
    arr = np.array(frames_features, dtype=np.float32)
    return arr[indices]
