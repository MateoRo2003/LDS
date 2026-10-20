"""
Junta ejemplos de una mano EN REPOSO (quieta a la altura de la cintura
mientras la otra hace una seña) y los deja en
datos/propio/manos_en_reposo.npz, para que entrenar_modelo.py se los
agregue a los clips.

Hace falta porque en LSA64 la mano que no participa casi nunca se
detecta (queda fuera de cuadro o MediaPipe no la ve con el guante), y
con una webcam en una mesa si se ve: el modelo tiene que aprender que
una mano quieta abajo no cambia la seña.

Salen de los videos de letras y numeros (senas_desde_videos.py): ahi una
mano hace las letras y la otra descansa todo el tiempo.

Uso:
    python manos_en_reposo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import numpy as np

import config
import senas_desde_videos as videos
from landmarks import features_de_secuencia, MANO_EN_REPOSO

SALIDA = os.path.join(config.PROYECTO, "datos", "propio", "manos_en_reposo.npz")
M = config.FEATURES_POR_MANO
MINIMO_FRAMES = 15


def espejar_mano(mano):
    """Una mano izquierda pasa a ser derecha: se invierten las x."""
    mano = mano.copy()
    mano[..., 0:M - 3:3] *= -1
    mano[..., M - 3] *= -1
    return mano


def tramos_en_reposo(video_id):
    """-> lista de secuencias (T, M) de una mano en reposo, todas como si fueran del lugar 0."""
    d = np.load(os.path.join(videos.CARPETA_CACHE, video_id + ".npz"))
    feats = features_de_secuencia(d["manos"], d["presente"], d["cuerpo"], d["cuerpo_ok"], float(d["aspecto"]))
    s = feats.reshape(len(feats), 2, M)
    presente = s[:, :, -1] > 0
    altura = s[:, :, M - 2]
    tramos = []
    for quieta, activa in ((0, 1), (1, 0)):
        # la mano quieta abajo y la otra levantada haciendo la seña
        ok = presente[:, quieta] & (altura[:, quieta] > MANO_EN_REPOSO) & \
            presente[:, activa] & (altura[:, activa] < MANO_EN_REPOSO)
        bordes = np.flatnonzero(np.diff(np.concatenate([[0], ok.astype(int), [0]])))
        for desde, hasta in zip(bordes[::2], bordes[1::2]):
            if hasta - desde >= MINIMO_FRAMES:
                tramo = s[desde:hasta, quieta]
                tramos.append(tramo if quieta == 0 else espejar_mano(tramo))
    return tramos


def main():
    tramos = []
    for video_id in videos.VIDEOS:
        de_este = tramos_en_reposo(video_id)
        print(f"{video_id}: {len(de_este)} tramos, {sum(map(len, de_este))} frames")
        tramos += de_este
    np.savez_compressed(SALIDA, frames=np.concatenate(tramos).astype(np.float32),
                        largos=np.array([len(t) for t in tramos]))
    print(f"{SALIDA}: {len(tramos)} tramos")


if __name__ == "__main__":
    main()
