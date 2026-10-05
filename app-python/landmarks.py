"""
Funciones compartidas para extraer y dibujar landmarks con MediaPipe
(API nueva "Tasks" — mp.solutions ya no existe desde mediapipe 1.0).
Usado tanto por extraer_landmarks.py (offline, sobre videos) como por
reconocedor.py (tiempo real, sobre la webcam).

Dos etapas, para que el entrenamiento y la app en vivo calculen
exactamente lo mismo:

1. crudo_de_resultados(): lo que devuelve MediaPipe en un frame, tal
   cual (coordenadas de la imagen). Es lo que se guarda en disco.
2. features_de_secuencia(): convierte una secuencia de frames crudos en
   lo que ve el modelo. Aca esta la clave para que funcione con
   cualquier camara: en vez de "en que parte de la imagen esta la mano",
   se usa la FORMA de la mano (relativa a la muñeca, sin importar su
   tamaño) y su posicion RESPECTO DE LA CARA (medida en anchos de
   hombros). Asi da lo mismo estar parado lejos, como en LSA64, o
   sentado cerca de la notebook.
"""
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

import config

PUNTOS_POR_MANO = 21
MUNECA = 0
NUDILLO_MEDIO = 9
# indices del modelo de pose: nariz y los dos hombros
PUNTOS_CUERPO = (0, 11, 12)


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


def crear_pose(running_mode=None):
    config.asegurar_modelo_pose()
    modo = running_mode or vision.RunningMode.VIDEO
    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=config.RUTA_MODELO_POSE),
        running_mode=modo,
    )
    return vision.PoseLandmarker.create_from_options(options)


def crudo_de_resultados(resultado_manos, resultado_pose):
    """
    Un frame -> (manos (2,21,3), presente (2,), cuerpo (3,2), cuerpo_ok).
    Las manos van ordenadas por handedness (indice 0 = "Left", 1 =
    "Right"), no por orden de deteccion: evita que salten de lugar entre
    frames por error del tracker, algo que confundiria mucho a la LSTM.
    """
    manos = np.zeros((2, PUNTOS_POR_MANO, 3), dtype=np.float32)
    presente = np.zeros(2, dtype=bool)
    for puntos, handedness in zip(resultado_manos.hand_landmarks, resultado_manos.handedness):
        i = 0 if handedness[0].category_name == "Left" else 1
        manos[i] = [[p.x, p.y, p.z] for p in puntos]
        presente[i] = True

    cuerpo = np.zeros((len(PUNTOS_CUERPO), 2), dtype=np.float32)
    cuerpo_ok = bool(resultado_pose.pose_landmarks)
    if cuerpo_ok:
        puntos = resultado_pose.pose_landmarks[0]
        cuerpo[:] = [[puntos[i].x, puntos[i].y] for i in PUNTOS_CUERPO]

    return manos, presente, cuerpo, cuerpo_ok


def features_de_secuencia(manos, presente, cuerpo, cuerpo_ok, aspecto):
    """
    Secuencia cruda de T frames -> array (T, FEATURES_POR_FRAME), o None
    si en ningun frame se vio el cuerpo (sin cara no hay referencia).

    aspecto = ancho/alto de la imagen: MediaPipe da x e y en [0,1], asi
    que sin corregirlo una mano mide distinto en un video 16:9 que en
    una webcam 4:3.
    """
    cuerpo_ok = np.asarray(cuerpo_ok, dtype=bool)
    if not cuerpo_ok.any():
        return None

    manos = np.array(manos, dtype=np.float32)
    manos[..., 0] *= aspecto
    manos[..., 2] *= aspecto  # z viene en la misma escala que x
    cuerpo = np.array(cuerpo, dtype=np.float32)[cuerpo_ok]
    cuerpo[..., 0] *= aspecto

    # Una sola referencia para toda la secuencia (la mediana): la cabeza
    # casi no se mueve durante una seña, y asi no molesta que la mano
    # tape la cara en algunos frames.
    nariz = np.median(cuerpo[:, 0], axis=0)
    ancho_hombros = np.median(np.linalg.norm(cuerpo[:, 1] - cuerpo[:, 2], axis=1))
    ancho_hombros = max(float(ancho_hombros), 1e-3)

    muneca = manos[:, :, MUNECA:MUNECA + 1, :]
    tamano = np.linalg.norm(manos[:, :, NUDILLO_MEDIO] - manos[:, :, MUNECA], axis=-1)
    tamano = np.maximum(tamano, 1e-4)[..., None, None]
    forma = ((manos - muneca) / tamano).reshape(len(manos), 2, -1)
    posicion = (manos[:, :, MUNECA, :2] - nariz) / ancho_hombros

    presente = np.asarray(presente, dtype=np.float32)[..., None]
    por_mano = np.concatenate([forma, posicion, np.ones_like(presente)], axis=-1) * presente
    return por_mano.reshape(len(manos), -1).astype(np.float32)


# Para las señas estaticas: una mano con la muñeca mas abajo que esto
# (en anchos de hombros desde la nariz) esta en reposo y no se cuenta.
MANO_EN_REPOSO = 1.1
PUNTA_INDICE = 8
FEATURES_POSTURA = 63 + 6 + 63 + 2 + 1


def posturas(frames_crudos, aspecto):
    """
    Para las señas estaticas (letras, numeros): lista de frames crudos
    -> (features (T, FEATURES_POSTURA), en cuales hay una mano haciendo
    seña), o (None, None) si no se ve el cuerpo. Cada frame se mira por
    separado.

    En LSA una letra no es solo la forma de la mano: tambien importa
    donde se hace (frente, oreja, menton, pecho) y algunas usan las dos
    manos. Por eso cada postura lleva:
    - la mano principal (la que esta mas arriba): su forma y donde estan
      su muñeca, la punta del indice y el centro de la palma respecto
      de la cara;
    - la otra mano, si esta levantada: su forma y donde esta respecto de
      la principal.
    Si la principal es la izquierda se espeja todo, para que la misma
    seña valga con cualquiera de las dos manos.
    """
    manos, presente, cuerpo, cuerpo_ok = (np.array(x) for x in zip(*frames_crudos))
    cuerpo_ok = cuerpo_ok.astype(bool)
    if not cuerpo_ok.any():
        return None, None

    manos = manos.astype(np.float32)
    manos[..., 0] *= aspecto
    manos[..., 2] *= aspecto
    cuerpo = cuerpo[cuerpo_ok].astype(np.float32)
    cuerpo[..., 0] *= aspecto
    nariz = np.median(cuerpo[:, 0], axis=0)
    ancho_hombros = max(float(np.median(np.linalg.norm(cuerpo[:, 1] - cuerpo[:, 2], axis=1))), 1e-3)

    lugar = (manos[..., :2] - nariz) / ancho_hombros            # (T, 2, 21, 2)
    tamano = np.maximum(np.linalg.norm(manos[:, :, NUDILLO_MEDIO] - manos[:, :, MUNECA], axis=-1), 1e-4)
    forma = (manos - manos[:, :, MUNECA:MUNECA + 1]) / tamano[..., None, None]

    levantada = presente.astype(bool) & (lugar[:, :, MUNECA, 1] < MANO_EN_REPOSO)
    hay_mano = levantada.any(axis=1)
    principal = np.argmin(np.where(levantada, lugar[:, :, MUNECA, 1], np.inf), axis=1)
    t = np.arange(len(manos))
    otra = 1 - principal
    hay_otra = levantada[t, otra].astype(np.float32)[:, None]

    espejo = np.where(principal == 0, -1.0, 1.0).astype(np.float32)[:, None, None]
    forma[..., 0] *= espejo
    lugar[..., 0] *= espejo

    feats = np.concatenate([
        forma[t, principal].reshape(len(t), -1),
        lugar[t, principal][:, [MUNECA, PUNTA_INDICE, NUDILLO_MEDIO]].reshape(len(t), -1),
        forma[t, otra].reshape(len(t), -1) * hay_otra,
        (lugar[t, otra, MUNECA] - lugar[t, principal, MUNECA]) * hay_otra,
        hay_otra,
    ], axis=1) * hay_mano[:, None]
    return feats.astype(np.float32), hay_mano


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
    arr = np.asarray(frames_features, dtype=np.float32)
    return arr[indices]
