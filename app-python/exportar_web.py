"""
Pasa los modelos entrenados a la version web (../signalis-web/).

La version web no usa TensorFlow: hace las cuentas de la red con
JavaScript propio (signalis-web/motor.js). Este script le deja:

- modelos/<categoria>.json: las capas de cada modelo con sus pesos.
- pruebas/casos.json: casos de prueba calculados aca, con Python, para
  que signalis-web/verificar.mjs compruebe que el JavaScript da los
  mismos numeros (features, probabilidades y señas detectadas en vivo).

Hay que volver a correrlo cada vez que se reentrena un modelo.

Uso:
    python exportar_web.py
"""
import base64
import glob
import json
import os
import shutil

import numpy as np
import tensorflow as tf

import config
import estaticas
from landmarks import features_de_secuencia, posturas, resamplear_secuencia
from reconocedor import SeguidorDeSena, categorias_disponibles

DESTINO = os.path.join(config.PROYECTO, "signalis-web")
UMBRAL = 0.6
FPS = 30


def tensor(arr):
    arr = np.asarray(arr, dtype="<f4")
    return {"forma": list(arr.shape), "datos": base64.b64encode(arr.tobytes()).decode()}


def lstm(capa):
    nucleo, recurrente, sesgo = capa.get_weights()
    return {"nucleo": tensor(nucleo), "recurrente": tensor(recurrente), "sesgo": tensor(sesgo)}


def capas_de(modelo):
    capas = []
    for capa in modelo.layers:
        if isinstance(capa, tf.keras.layers.Bidirectional):
            capas.append({"tipo": "bilstm", "unidades": capa.forward_layer.units,
                          "secuencia": bool(capa.forward_layer.return_sequences),
                          "adelante": lstm(capa.forward_layer), "atras": lstm(capa.backward_layer)})
        elif isinstance(capa, tf.keras.layers.Dense):
            pesos, sesgo = capa.get_weights()
            capas.append({"tipo": "densa", "activacion": capa.activation.__name__,
                          "pesos": tensor(pesos), "sesgo": tensor(sesgo)})
        elif not isinstance(capa, tf.keras.layers.Dropout):  # dropout no hace nada al reconocer
            raise ValueError(f"Capa que la version web no sabe calcular: {type(capa).__name__}")
    return capas


def lista(arr, decimales=6):
    return np.round(np.asarray(arr, dtype=np.float64), decimales).tolist()


def frames_json(frames):
    return [{"manos": lista(m), "presente": [bool(p) for p in pr], "cuerpo": lista(c), "cuerpo_ok": bool(ok)}
            for m, pr, c, ok in frames]


def caso_dinamico(categoria, modelo, clases, ruta):
    """Un clip de LSA64: sus features, lo que dice el modelo y lo que detecta el seguidor en vivo."""
    d = np.load(ruta)
    aspecto = float(d["aspecto"])
    frames = list(zip(d["manos"], d["presente"], d["cuerpo"], d["cuerpo_ok"]))
    feats = features_de_secuencia(d["manos"], d["presente"], d["cuerpo"], d["cuerpo_ok"], aspecto)
    entrada = resamplear_secuencia(feats)
    probs = modelo(entrada[None], training=False).numpy()[0]

    seguidor = SeguidorDeSena(modelo, clases, aspecto)
    vacio = (np.zeros_like(d["manos"][0]), np.zeros(2, dtype=bool), d["cuerpo"][-1], True)
    en_vivo = frames + [vacio] * FPS
    detectadas = []
    for i, frame in enumerate(en_vivo):
        seguidor.procesar(i / FPS, frame, UMBRAL)
        if seguidor.nueva:
            detectadas.append(seguidor.detectada[0])
    return {"categoria": categoria, "tipo": "dinamica", "origen": os.path.basename(ruta), "aspecto": aspecto,
            "frames": frames_json(en_vivo), "cuantos_del_clip": len(frames),
            "features": lista(feats), "entrada": lista(entrada), "probs": lista(probs), "detectadas": detectadas}


def caso_estatico(categoria, modelo, clases, video_id, desde, hasta):
    """Un tramo de un video de letras o numeros, con varias señas seguidas."""
    d = np.load(os.path.join(config.PROYECTO, "datos", "procesado", "videos_senas", video_id + ".npz"))
    en_tramo = (d["tiempos"] >= desde) & (d["tiempos"] < hasta)
    frames = list(zip(d["manos"][en_tramo], d["presente"][en_tramo], d["cuerpo"][en_tramo], d["cuerpo_ok"][en_tramo]))
    tiempos = d["tiempos"][en_tramo]
    aspecto = float(d["aspecto"])
    feats, con_mano = posturas(frames, aspecto)

    seguidor = estaticas.SeguidorEstatico(modelo, clases, aspecto)
    detectadas, confianzas = [], []
    for t, frame in zip(tiempos, frames):
        seguidor.procesar(float(t), frame, UMBRAL)
        confianzas.append(seguidor.confianza)
        if seguidor.nueva:
            detectadas.append(seguidor.detectada[0])
    return {"categoria": categoria, "tipo": "estatica", "origen": video_id, "aspecto": aspecto,
            "frames": frames_json(frames), "tiempos": lista(tiempos),
            "features": lista(feats), "con_mano": [bool(x) for x in con_mano],
            "probs": lista(modelo(feats, training=False).numpy()),
            "confianzas": lista(confianzas), "detectadas": detectadas}


def main():
    os.makedirs(os.path.join(DESTINO, "modelos"), exist_ok=True)
    os.makedirs(os.path.join(DESTINO, "pruebas"), exist_ok=True)
    casos = []

    for categoria in categorias_disponibles():
        modelo = tf.keras.models.load_model(config.ruta_modelo(categoria))
        with open(config.ruta_etiquetas(categoria), encoding="utf-8") as f:
            etiquetas = json.load(f)
        clases = etiquetas["clases"]
        estatica = etiquetas.get("tipo") == "estatica"
        titulo, tipo_sena = config.INFO_CATEGORIAS[categoria]
        with open(os.path.join(DESTINO, "modelos", categoria + ".json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": categoria, "titulo": titulo, "tipo_sena": tipo_sena, "estatica": estatica,
                "clases": clases,
                "nombres": [None if c == config.CLASE_NADA else config.palabra_es(c) for c in clases],
                "capas": capas_de(modelo),
            }, f, ensure_ascii=False)
        print(f"{categoria}: {len(clases)} clases exportadas")

        if estatica:
            video_id, (desde, hasta) = {"abecedario": ("bhzaMJw_NbE", (16.0, 62.0)),
                                        "numeros": ("gLSSENEOGD4", (16.0, 58.0))}[categoria]
            casos.append(caso_estatico(categoria, modelo, clases, video_id, desde, hasta))
        else:
            # dos clips de cada seña, de las personas que el modelo no vio
            for carpeta in config.vocabulario(categoria)[:6]:
                for ruta in sorted(glob.glob(os.path.join(config.CARPETA_CRUDO, carpeta, "*_009_00[12].npz"))):
                    casos.append(caso_dinamico(categoria, modelo, clases, ruta))

    with open(os.path.join(DESTINO, "pruebas", "casos.json"), "w", encoding="utf-8") as f:
        json.dump(casos, f)
    print(f"{len(casos)} casos de prueba")

    # los modelos de MediaPipe que ubican manos y cuerpo: los mismos archivos que usa Python
    for ruta in (config.RUTA_MODELO_LANDMARKER, config.RUTA_MODELO_POSE):
        shutil.copy(ruta, os.path.join(DESTINO, "modelos", os.path.basename(ruta)))


if __name__ == "__main__":
    main()
