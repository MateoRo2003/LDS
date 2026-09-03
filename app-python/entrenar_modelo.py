"""
Entrena un clasificador (Bi-LSTM chico) sobre el dataset de landmarks
de una categoria (generado por extraer_landmarks.py --categoria X), y
guarda el modelo entrenado para esa categoria.

Separa entrenamiento y validacion POR PERSONA (no al azar): dejamos
afuera del entrenamiento a las 2 ultimas personas de LSA64 (sujetos 9 y
10) y validamos solo con ellas. Esto simula lo que va a pasar en la
expo — alguien que el modelo nunca vio grabar — en vez de inflar la
metrica validando con la misma gente que ya vio entrenando.

Uso:
    python entrenar_modelo.py --categoria colores
    python entrenar_modelo.py --categoria prueba   (default)
"""
import argparse
import json
import os
import re

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import (
    Bidirectional, Dense, Dropout, LSTM, Masking,
)
from tensorflow.keras.models import Sequential
from tensorflow.keras.utils import to_categorical

import config

PERSONAS_VALIDACION = {9, 10}  # sujetos de LSA64 reservados para validar


def persona_de_nombre(nombre_archivo):
    # nombre_archivo tipo "051-thanks/051_005_003.mp4" -> persona = 005
    m = re.search(r"_(\d{3})_\d{3}\.mp4$", nombre_archivo)
    return int(m.group(1)) if m else None


def main(categoria):
    ruta_dataset = config.ruta_dataset(categoria)
    if not os.path.exists(ruta_dataset):
        raise FileNotFoundError(
            f"No existe {ruta_dataset} — corré primero: python extraer_landmarks.py --categoria {categoria}"
        )

    data = np.load(ruta_dataset, allow_pickle=True)
    X, y = data["X"], data["y"]
    clases = list(data["clases"])
    nombres = list(data["nombres_archivo"])

    personas = np.array([persona_de_nombre(n) for n in nombres])
    es_val = np.isin(personas, list(PERSONAS_VALIDACION))

    X_train, y_train = X[~es_val], y[~es_val]
    X_val, y_val = X[es_val], y[es_val]

    print(f"Categoria: {categoria}")
    print(f"Train: {X_train.shape[0]} clips | Val (personas {sorted(PERSONAS_VALIDACION)}): {X_val.shape[0]} clips")
    print(f"Clases ({len(clases)}): {clases}")

    # Normalizacion simple: las coordenadas de MediaPipe ya vienen en
    # [0,1] (x,y) / rango chico (z), pero centramos y escalamos igual
    # para que la red converja mas rapido.
    media = X_train.mean(axis=(0, 1), keepdims=True)
    std = X_train.std(axis=(0, 1), keepdims=True) + 1e-6
    X_train = (X_train - media) / std
    X_val = (X_val - media) / std

    num_clases = len(clases)
    y_train_oh = to_categorical(y_train, num_clases)
    y_val_oh = to_categorical(y_val, num_clases)

    modelo = Sequential([
        Masking(mask_value=0.0, input_shape=(config.LONGITUD_SECUENCIA, config.FEATURES_POR_FRAME)),
        Bidirectional(LSTM(64, return_sequences=True, dropout=0.3)),
        Bidirectional(LSTM(32, dropout=0.3)),
        Dense(64, activation="relu"),
        Dropout(0.4),
        Dense(num_clases, activation="softmax"),
    ])
    modelo.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    modelo.summary()

    parada = EarlyStopping(monitor="val_accuracy", patience=15, restore_best_weights=True)

    modelo.fit(
        X_train, y_train_oh,
        validation_data=(X_val, y_val_oh),
        epochs=100,
        batch_size=16,
        callbacks=[parada],
        verbose=2,
    )

    nombres_legibles = [config.palabra_es(c) for c in clases]

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
        json.dump({
            "clases": clases,
            "media": media.tolist(),
            "std": std.tolist(),
        }, f, ensure_ascii=False, indent=2)

    print(f"\nModelo guardado en {ruta_modelo}")
    print(f"Etiquetas + normalizacion guardadas en {ruta_etiquetas}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", default="prueba", help="Nombre de categoria en config.CATEGORIAS")
    args = parser.parse_args()
    main(args.categoria)
