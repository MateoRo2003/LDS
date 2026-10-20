"""
Arma clips de señas CON MOVIMIENTO (saludos y preguntas) a partir de
videos donde una persona muestra cada seña, para sumarlas a las de LSA64.

Cada tramo se corta de los landmarks del video entero (los mismos que
calcula senas_desde_videos.py, en datos/procesado/videos_senas/) y se
guarda en datos/procesado/crudo/<carpeta>/ con el formato y el nombre de
un clip de LSA64, asi entrenar_modelo.py los usa sin cambios:

- Una seña nueva va a su propia carpeta (101-hola, 102-chau, ...).
- Una seña que ya esta en LSA64 (gracias, donde) va a la carpeta de
  LSA64 como un clip mas, de otra persona.

Cada persona de estos videos lleva un numero propio (LSA64 usa del 1 al
10) y la repeticion 1 es la forma principal; las variantes que muestra
el video son la repeticion 2.

Los tramos se marcaron mirando el video y donde la persona levanta las
manos del reposo (las tiene juntas a la altura de la cintura entre seña
y seña).

Uso:
    python palabras_desde_videos.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import numpy as np

import config
import senas_desde_videos as videos

VIDEOS = {
    # "SALUDOS Y FÓRMULAS DE CORTESÍA EN LSA", Direccion de Documentacion
    # https://www.youtube.com/watch?v=g18JlOMg5Lk
    "g18JlOMg5Lk": {
        "persona": 11,
        "senas": {
            "101-hola": [(13.8, 15.8)],
            "102-chau": [(17.8, 19.9)],
            "103-buen-dia": [(21.8, 23.8)],
            "104-buenas-tardes": [(26.6, 28.5)],
            "105-buenas-noches": [(29.8, 31.7)],
            "106-hasta-manana": [(33.3, 36.7)],
            "051-thanks": [(40.7, 42.5)],
            "107-muchas-gracias": [(43.8, 45.7)],
            "108-por-favor": [(47.5, 49.4), (49.4, 51.2)],
            "109-lo-siento": [(52.3, 55.7)],
            "110-felicitaciones": [(57.0, 59.5), (59.6, 61.7)],
            "111-perdon": [(63.5, 65.9), (65.9, 67.9)],
            "112-bienvenidos": [(70.1, 72.5)],
        },
    },
    # "ORGANIZADORES DE PREGUNTAS EN LSA", Direccion de Documentacion
    # https://www.youtube.com/watch?v=x57rpA804yA
    "x57rpA804yA": {
        "persona": 12,
        "senas": {
            "121-cuando": [(13.6, 15.7)],
            "122-como": [(19.5, 21.6)],
            "123-cuantos": [(23.3, 25.5)],
            "124-cual": [(27.9, 30.45)],
            "125-cual-de-los-dos": [(30.45, 32.5)],
            "126-quien": [(33.5, 35.5)],
            "127-que": [(37.4, 39.2)],
            "128-por-que": [(42.4, 44.4)],
            "028-where": [(46.3, 48.8)],
        },
    },
}


def main():
    for video_id, info in VIDEOS.items():
        d = np.load(os.path.join(videos.CARPETA_CACHE, video_id + ".npz"))
        for carpeta, tramos in info["senas"].items():
            os.makedirs(os.path.join(config.CARPETA_CRUDO, carpeta), exist_ok=True)
            for repeticion, (desde, hasta) in enumerate(tramos, 1):
                tramo = (d["tiempos"] >= desde) & (d["tiempos"] < hasta)
                nombre = f"{carpeta[:3]}_{info['persona']:03d}_{repeticion:03d}.npz"
                np.savez_compressed(os.path.join(config.CARPETA_CRUDO, carpeta, nombre),
                                    manos=d["manos"][tramo], presente=d["presente"][tramo],
                                    cuerpo=d["cuerpo"][tramo], cuerpo_ok=d["cuerpo_ok"][tramo],
                                    aspecto=d["aspecto"])
                print(f"{carpeta}/{nombre}: {tramo.sum()} frames")


if __name__ == "__main__":
    main()
