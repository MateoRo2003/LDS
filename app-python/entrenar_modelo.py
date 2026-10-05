"""
Entrena un clasificador (Bi-LSTM chico) para una categoria, a partir de
los landmarks crudos que dejo extraer_landmarks.py --categoria X, y
guarda el modelo entrenado para esa categoria.

Separa entrenamiento y validacion POR PERSONA (no al azar): dejamos
afuera del entrenamiento a las 2 ultimas personas de LSA64 (sujetos 9 y
10) y validamos solo con ellas. Esto simula lo que va a pasar en la
expo — alguien que el modelo nunca vio grabar — en vez de inflar la
metrica validando con la misma gente que ya vio entrenando.

Ademas de las señas de la categoria, el modelo aprende una clase
"nada" (config.CLASE_NADA) con dos tipos de ejemplos: otras señas de
LSA64 y manos quietas. Sin eso, cualquier mano frente a la camara
termina siendo alguna palabra de la categoria.

Uso:
    python entrenar_modelo.py --categoria colores
"""
import argparse
import json
import os

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras.layers import Bidirectional, Dense, Dropout, Input, LSTM
from tensorflow.keras.models import Sequential

import config
from extraer_landmarks import clips_de_categoria, partes_de_nombre, ruta_crudo
from landmarks import features_de_secuencia, resamplear_secuencia

PERSONAS_VALIDACION = {9, 10}  # sujetos de LSA64 reservados para validar

EPOCAS = 150
PACIENCIA = 25
COPIAS_POR_SENA = 4       # versiones aumentadas de cada clip de la categoria, por epoca
QUIETAS_POR_CLIP = 0.4    # ejemplos de "mano quieta" por cada clip disponible

M = config.FEATURES_POR_MANO
FORMA = slice(0, M - 3)
POS = slice(M - 3, M - 1)


def cargar_clips(categoria):
    """-> lista de (features (T, F), indice de clase, persona)."""
    vocab = config.vocabulario(categoria)
    clips, faltan, sin_cuerpo = [], 0, 0
    for carpeta, nombre in clips_de_categoria(categoria):
        ruta = ruta_crudo(carpeta, nombre)
        if not os.path.exists(ruta):
            faltan += 1
            continue
        d = np.load(ruta)
        feats = features_de_secuencia(d["manos"], d["presente"], d["cuerpo"], d["cuerpo_ok"], float(d["aspecto"]))
        if feats is None:
            sin_cuerpo += 1
            continue
        clase = vocab.index(carpeta) if carpeta in vocab else len(vocab)
        clips.append((feats, clase, partes_de_nombre(nombre)[0]))
    if faltan:
        raise SystemExit(f"Faltan {faltan} clips sin extraer — corré primero: "
                         f"python extraer_landmarks.py --categoria {categoria}")
    if sin_cuerpo:
        print(f"[AVISO] {sin_cuerpo} clips descartados: no se detecto el cuerpo en ningun frame")
    return clips


def espejar(sec):
    """Como si la seña la hiciera un zurdo: invierte x y cruza las manos."""
    s = sec.reshape(len(sec), 2, M).copy()
    s[:, :, 0:M - 3:3] *= -1
    s[:, :, M - 3] *= -1
    return s[:, ::-1].reshape(len(sec), -1)


def aumentar(feats, rng):
    """
    Variante al azar de un clip, ya en LONGITUD_SECUENCIA frames. Imita
    lo que cambia en vivo: la seña no arranca ni termina justo en los
    bordes de la ventana, cada persona la hace en un lugar y tamaño
    apenas distinto, y la deteccion de la mano tiembla o se pierde.
    """
    total = len(feats)
    desde = int(rng.uniform(0, 0.2) * total)
    hasta = total - int(rng.uniform(0, 0.2) * total)
    sec = resamplear_secuencia(feats[desde:max(hasta, desde + 2)])
    if rng.random() < 0.5:
        sec = espejar(sec)

    s = sec.reshape(len(sec), 2, M).copy()
    presente = s[:, :, -1:].copy()

    angulo = np.deg2rad(rng.normal(0, 8))
    cos, sen = np.cos(angulo), np.sin(angulo)
    forma = s[:, :, FORMA].reshape(len(s), 2, -1, 3)
    x, y = forma[..., 0].copy(), forma[..., 1].copy()
    forma[..., 0] = cos * x - sen * y
    forma[..., 1] = sen * x + cos * y
    forma *= rng.uniform(0.9, 1.1)
    forma += rng.normal(0, 0.03, forma.shape)
    s[:, :, FORMA] = forma.reshape(len(s), 2, -1)

    s[:, :, POS] = s[:, :, POS] * rng.uniform(0.85, 1.2) + rng.normal(0, 0.12, 2)
    s[:, :, POS] += rng.normal(0, 0.02, s[:, :, POS].shape)

    if rng.random() < 0.3:  # la mano se pierde unos frames
        inicio = rng.integers(0, len(s) - 3)
        presente[inicio:inicio + rng.integers(1, 4), rng.integers(0, 2)] = 0

    return (s * presente).reshape(len(sec), -1).astype(np.float32)


def mano_quieta(feats, rng):
    """Un frame con mano, repetido: una pose sostenida no es una seña."""
    con_mano = np.flatnonzero(feats.reshape(len(feats), 2, M)[:, :, -1].any(axis=1))
    if len(con_mano) == 0:
        return None
    frame = feats[rng.choice(con_mano)]
    return aumentar(np.repeat(frame[None], config.LONGITUD_SECUENCIA, axis=0), rng)


def armar_conjunto(clips, clase_nada, rng, copias):
    X, y = [], []
    for feats, clase, _ in clips:
        for _ in range(copias if clase != clase_nada else 1):
            X.append(aumentar(feats, rng))
            y.append(clase)
    for i in rng.choice(len(clips), int(len(clips) * QUIETAS_POR_CLIP), replace=False):
        quieta = mano_quieta(clips[i][0], rng)
        if quieta is not None:
            X.append(quieta)
            y.append(clase_nada)
    return np.array(X), np.array(y)


def main(categoria):
    vocab = config.vocabulario(categoria)
    clases = list(vocab) + [config.CLASE_NADA]
    clase_nada = len(vocab)

    clips = cargar_clips(categoria)
    train = [c for c in clips if c[2] not in PERSONAS_VALIDACION]
    val = [c for c in clips if c[2] in PERSONAS_VALIDACION]

    # Validacion fija: los clips enteros sin tocar + manos quietas.
    rng_val = np.random.default_rng(0)
    X_val = [resamplear_secuencia(f) for f, _, _ in val]
    y_val = [c for _, c, _ in val]
    for feats, _, _ in val[::3]:
        quieta = mano_quieta(feats, rng_val)
        if quieta is not None:
            X_val.append(quieta)
            y_val.append(clase_nada)
    X_val, y_val = np.array(X_val), np.array(y_val)

    print(f"Categoria: {categoria}")
    print(f"Train: {len(train)} clips | Val (personas {sorted(PERSONAS_VALIDACION)}): {len(X_val)} secuencias")
    print(f"Clases ({len(clases)}): {clases}")

    modelo = Sequential([
        Input(shape=(config.LONGITUD_SECUENCIA, config.FEATURES_POR_FRAME)),
        Bidirectional(LSTM(64, return_sequences=True, dropout=0.3)),
        Bidirectional(LSTM(32, dropout=0.3)),
        Dense(64, activation="relu"),
        Dropout(0.4),
        Dense(len(clases), activation="softmax"),
    ])
    modelo.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    # Cada epoca ve versiones aumentadas nuevas de los mismos clips.
    rng = np.random.default_rng(1)
    mejor_acc, mejores_pesos, sin_mejorar = -1.0, None, 0
    for epoca in range(1, EPOCAS + 1):
        X_train, y_train = armar_conjunto(train, clase_nada, rng, COPIAS_POR_SENA)
        h = modelo.fit(X_train, y_train, validation_data=(X_val, y_val),
                       epochs=1, batch_size=32, verbose=0).history
        acc = h["val_accuracy"][0]
        print(f"epoca {epoca:3d}  loss {h['loss'][0]:.3f}  acc {h['accuracy'][0]:.3f}  val_acc {acc:.3f}", flush=True)
        if acc > mejor_acc:
            mejor_acc, mejores_pesos, sin_mejorar = acc, modelo.get_weights(), 0
        else:
            sin_mejorar += 1
            if sin_mejorar >= PACIENCIA:
                break
    modelo.set_weights(mejores_pesos)

    nombres_legibles = [config.palabra_es(c) for c in vocab] + ["(nada)"]

    print("\n=== Evaluacion en validacion (personas nunca vistas en train) ===")
    y_pred = np.argmax(modelo.predict(X_val, verbose=0), axis=1)
    print(classification_report(y_val, y_pred, target_names=nombres_legibles, digits=3))
    print("Matriz de confusion (filas=real, columnas=predicho):")
    print(nombres_legibles)
    print(confusion_matrix(y_val, y_pred))

    ruta_modelo = config.ruta_modelo(categoria)
    ruta_etiquetas = config.ruta_etiquetas(categoria)
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)
    modelo.save(ruta_modelo)

    with open(ruta_etiquetas, "w", encoding="utf-8") as f:
        json.dump({"clases": clases}, f, ensure_ascii=False, indent=2)

    print(f"\nModelo guardado en {ruta_modelo}")
    print(f"Etiquetas guardadas en {ruta_etiquetas}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", required=True, help="Nombre de categoria en config.CATEGORIAS")
    args = parser.parse_args()
    main(args.categoria)
