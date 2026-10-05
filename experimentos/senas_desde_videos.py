"""
Arma las muestras del ABECEDARIO y de los NUMEROS a partir de videos
donde una persona muestra cada seña de LSA, en vez de grabarlas con la
app.

Los videos van en datos/externos/videos_senas/ (ver VIDEOS: de donde
salio cada uno y en que tramo, en segundos, esta cada seña). Los tramos
se marcaron mirando el video; a cada uno se le recorta un margen al
principio y al final para dejar afuera la mano subiendo y bajando. Del
abecedario no estan CH ni LL.

Deja las muestras en datos/propio/estaticas/<categoria>/, en el mismo
formato que las grabaciones hechas desde la app, asi que despues se
puede seguir sumando grabaciones propias y volver a entrenar.

No arma ejemplos de "ninguna seña": probado con posturas de LSA64 y con
las partes habladas de los mismos videos, y en los dos casos el modelo
terminaba mandando a "ninguna" las señas de una persona nueva.
"Ninguna" se puede grabar desde la app.

Uso:
    python senas_desde_videos.py            extrae, arma las muestras y entrena
    python senas_desde_videos.py --evaluar  ademas mide cuanto generaliza a otra persona
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import cv2
import numpy as np
import mediapipe as mp

import config
import estaticas
from landmarks import crear_landmarker, crear_pose, crudo_de_resultados

CARPETA_VIDEOS = os.path.join(config.PROYECTO, "datos", "externos", "videos_senas")
CARPETA_CACHE = os.path.join(config.PROYECTO, "datos", "procesado", "videos_senas")

# margen: segundos que se descartan a cada lado del tramo.
# recorte: (x0, y0, x1, y1) en fracciones de la imagen, cuando la persona
# ocupa solo una parte del video.
VIDEOS = {
    # "Abecedario LSA", Direccion de Inclusion Educativa, Universidad Popular
    # https://www.facebook.com/watch/?v=265056705412909
    "265056705412909": {
        "categoria": "abecedario", "margen": 0,
        "senas": {
            "A": (55.0, 55.7), "B": (56.3, 57.2), "C": (57.4, 58.2), "D": (60.0, 60.7),
            "E": (61.4, 62.2), "F": (62.9, 63.7), "G": (64.0, 65.1), "H": (65.4, 66.2),
            "I": (66.9, 67.7), "J": (68.0, 69.2), "K": (69.5, 70.7), "L": (71.0, 72.7),
            "M": (74.0, 74.7), "N": (75.0, 75.7), "Ñ": (76.0, 77.2), "O": (77.4, 78.2),
            "P": (78.5, 79.7), "Q": (80.0, 81.2), "R": (81.5, 82.7), "S": (83.0, 84.2),
            "T": (84.5, 85.7), "U": (86.0, 87.2), "V": (87.5, 88.2), "W": (88.6, 90.2),
            "X": (90.5, 91.7), "Y": (92.0, 93.2), "Z": (93.5, 94.7),
        },
    },
    # "Lengua de señas Argentina LSA Clase 1 ABCedario"
    # https://www.youtube.com/watch?v=YKHsz05061I
    "YKHsz05061I": {
        "categoria": "abecedario", "margen": 0,
        "senas": {
            "A": (38.0, 39.7), "B": (40.0, 41.2), "C": (41.5, 44.2), "D": (44.5, 47.2),
            "E": (47.5, 48.7), "F": (49.5, 50.7), "G": (51.5, 52.7), "H": (53.0, 55.2),
            "I": (55.5, 56.2), "J": (56.5, 58.7), "K": (59.2, 60.7), "L": (61.0, 62.2),
            "M": (64.5, 66.2), "N": (66.5, 67.7), "Ñ": (68.0, 71.2), "O": (71.5, 73.2),
            "P": (73.5, 76.7), "Q": (77.5, 79.2), "R": (79.5, 81.7), "S": (82.5, 84.2),
            "T": (84.6, 86.2), "U": (86.5, 88.7), "V": (91.5, 94.0), "W": (94.5, 98.0),
            "X": (98.5, 100.2), "Y": (101.0, 103.2), "Z": (103.5, 105.2),
        },
    },
    # "ALFABETO DACTILOLOGICO LSA", Direccion de Documentacion
    # https://www.youtube.com/watch?v=bhzaMJw_NbE
    # La persona baja las manos entre letra y letra: cada tramo es desde
    # que las levanta hasta que las baja.
    "bhzaMJw_NbE": {
        "categoria": "abecedario", "margen": 0.3,
        "senas": {
            "A": (17.4, 18.8), "B": (21.4, 22.6), "C": (25.4, 26.8), "D": (34.4, 38.0),
            "E": (40.5, 42.1), "F": (44.3, 46.5), "G": (49.3, 51.2), "H": (53.7, 56.0),
            "I": (58.4, 60.5), "J": (63.2, 65.2), "K": (68.0, 69.8), "L": (72.3, 73.9),
            "M": (83.6, 85.4), "N": (87.5, 89.3), "Ñ": (92.2, 94.6), "O": (97.2, 99.3),
            "P": (101.0, 103.8), "Q": (106.7, 108.4), "R": (111.2, 112.9), "S": (115.4, 117.5),
            "T": (120.3, 122.4), "U": (125.1, 127.0), "V": (129.4, 131.4), "W": (133.8, 135.8),
            "X": (138.4, 140.5), "Y": (142.9, 145.4), "Z": (148.4, 153.1),
        },
    },
    # "NUMEROS EN LSA", Direccion de Documentacion
    # https://www.youtube.com/watch?v=gLSSENEOGD4
    "gLSSENEOGD4": {
        "categoria": "numeros", "margen": 0.3,
        "senas": {
            "0": (17.2, 20.6), "1": (22.9, 24.6), "2": (26.8, 28.4), "3": (30.2, 31.8),
            "4": (33.4, 35.2), "5": (37.4, 38.9), "6": (40.7, 42.5), "7": (44.2, 46.1),
            "8": (47.8, 49.7), "9": (51.5, 53.3), "10": (54.8, 56.8),
        },
    },
    # "Numeros en LSA - Lengua de Señas Argentina", Carolina Sarria
    # https://www.youtube.com/watch?v=9ghx0rmFKKg
    "9ghx0rmFKKg": {
        "categoria": "numeros", "margen": 0, "recorte": (0.45, 0.16, 0.93, 0.69),
        "senas": {
            "0": (34.2, 35.0), "1": (35.6, 37.2), "2": (37.6, 39.7), "3": (40.0, 41.7),
            "4": (42.4, 44.2), "5": (44.3, 45.0), "6": (45.4, 47.6), "7": (48.0, 49.7),
            "8": (50.4, 52.2), "9": (53.4, 55.2), "10": (55.6, 58.2),
        },
    },
}


def crudo_del_video(video_id):
    """Landmarks de todo el video (se calculan una sola vez). -> (tiempos, frames crudos, aspecto)"""
    cache = os.path.join(CARPETA_CACHE, video_id + ".npz")
    if not os.path.exists(cache):
        print(f"Extrayendo landmarks de {video_id}...")
        landmarker, pose = crear_landmarker(), crear_pose()
        cap = cv2.VideoCapture(os.path.join(CARPETA_VIDEOS, video_id + ".mp4"))
        fps = cap.get(cv2.CAP_PROP_FPS)
        x0, y0, x1, y1 = VIDEOS[video_id].get("recorte", (0, 0, 1, 1))
        tiempos, frames, aspecto = [], [], 1.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            alto, ancho = frame.shape[:2]
            frame = frame[int(y0 * alto):int(y1 * alto), int(x0 * ancho):int(x1 * ancho)]
            aspecto = frame.shape[1] / frame.shape[0]
            ms = int(len(tiempos) * 1000.0 / fps)
            imagen = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            frames.append(crudo_de_resultados(landmarker.detect_for_video(imagen, ms),
                                              pose.detect_for_video(imagen, ms)))
            tiempos.append(ms / 1000.0)
        cap.release()
        landmarker.close()
        pose.close()
        manos, presente, cuerpo, cuerpo_ok = zip(*frames)
        os.makedirs(CARPETA_CACHE, exist_ok=True)
        np.savez_compressed(cache, tiempos=tiempos, manos=manos, presente=presente,
                            cuerpo=cuerpo, cuerpo_ok=cuerpo_ok, aspecto=aspecto)
    d = np.load(cache)
    return d["tiempos"], list(zip(d["manos"], d["presente"], d["cuerpo"], d["cuerpo_ok"])), float(d["aspecto"])


def armar_muestras():
    for video_id, info in VIDEOS.items():
        tiempos, frames, aspecto = crudo_del_video(video_id)
        cuantos = []
        for sena, (desde, hasta) in info["senas"].items():
            desde, hasta = desde + info["margen"], hasta - info["margen"]
            tramo = [f for t, f in zip(tiempos, frames) if desde <= t < hasta]
            cuantos.append(estaticas.guardar(info["categoria"], sena, tramo, aspecto, nombre=f"video_{video_id}"))
        pocos = [s for s, n in zip(info["senas"], cuantos) if n < 8]
        print(f"{video_id} ({info['categoria']}): entre {min(cuantos)} y {max(cuantos)} frames por seña"
              + (f" — con muy pocos: {' '.join(pocos)}" if pocos else ""))


def evaluar(categoria):
    """Deja afuera un video por vez: entrena con los demas y prueba con ese (otra persona)."""
    carpeta = os.path.join(config.CARPETA_ESTATICAS, categoria)
    ids = [v for v, info in VIDEOS.items() if info["categoria"] == categoria]
    senas = list(VIDEOS[ids[0]]["senas"])

    def cargar(video_ids):
        X, y = [], []
        for video_id in video_ids:
            for i, sena in enumerate(senas):
                ruta = os.path.join(carpeta, sena, f"video_{video_id}.npy")
                if os.path.exists(ruta):
                    datos = np.load(ruta)
                    X.append(datos)
                    y.append(np.full(len(datos), i))
        return np.concatenate(X), np.concatenate(y)

    print(f"\n=== {categoria}: probando con una persona que el modelo no vio ===")
    for prueba in ids:
        X_test, y_test = cargar([prueba])
        modelo = estaticas.entrenar_red(*cargar([v for v in ids if v != prueba]), len(senas))
        pred = modelo.predict(X_test, verbose=0).argmax(axis=1)
        # una seña cuenta como reconocida si la mayoria de sus frames acierta
        fallan = []
        for i, sena in enumerate(senas):
            if (y_test == i).any():
                mas_votada = np.bincount(pred[y_test == i], minlength=len(senas)).argmax()
                if mas_votada != i:
                    fallan.append(f"{sena}>{senas[mas_votada]}")
        print(f"{prueba}: {len(senas) - len(fallan)} de {len(senas)} señas reconocidas, "
              f"{100 * (pred == y_test).mean():.0f}% de los frames."
              + (f" Fallan (seña>lo que dijo): {' '.join(fallan)}" if fallan else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluar", action="store_true")
    args = parser.parse_args()
    armar_muestras()
    categorias = sorted({info["categoria"] for info in VIDEOS.values()})
    if args.evaluar:
        for categoria in categorias:
            evaluar(categoria)
    print()
    for categoria in categorias:
        aprendidas, _ = estaticas.entrenar(categoria)
        print(f"Modelo de '{categoria}' entrenado: {len(aprendidas)} señas.")
