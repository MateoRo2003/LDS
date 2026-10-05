"""
Prueba de humo del reconocimiento EN VIVO sin necesitar una camara: le
pasa clips a SeguidorDeSena frame por frame, con sus tiempos reales,
igual que se los pasa la webcam en app.py (ventana deslizante, umbral,
suavizado y todo). No es lo mismo que evaluar el modelo con el clip
entero y recortado, que es lo que mide entrenar_modelo.py.

Usa los clips de las personas que el modelo nunca vio (las de
validacion) y reporta dos cosas:
- señas de la categoria: cuantas reconoce bien, cuantas confunde y
  cuantas deja pasar sin decir nada;
- señas de OTRAS categorias: cuantas veces se inventa una palabra.

Uso:
    python smoke_test_reconocimiento.py colores
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import numpy as np

import config
from entrenar_modelo import PERSONAS_VALIDACION
from extraer_landmarks import clips_de_categoria, partes_de_nombre, ruta_crudo
from reconocedor import Reconocedor, SeguidorDeSena, SIN_MANO_S

UMBRAL = 0.6


def palabras_detectadas(modelo, clases, crudo):
    """Pasa un clip como si fuera la camara y devuelve las señas que fue mostrando."""
    seguidor = SeguidorDeSena(modelo, clases, float(crudo["aspecto"]))
    vistas = []
    total = len(crudo["manos"])
    # al final se agrega un rato sin manos, como cuando la persona las baja
    cola = int((SIN_MANO_S + 0.3) * config.FPS_OBJETIVO)
    for i in range(total + cola):
        if i < total:
            frame = (crudo["manos"][i], crudo["presente"][i], crudo["cuerpo"][i], crudo["cuerpo_ok"][i])
        else:
            frame = (np.zeros_like(crudo["manos"][0]), np.zeros(2, dtype=bool), crudo["cuerpo"][-1], True)
        seguidor.procesar(i / config.FPS_OBJETIVO, frame, UMBRAL)
        if seguidor.nueva:
            vistas.append(clases[seguidor.detectada[0]])
    return vistas


def main(categoria):
    vocab = config.vocabulario(categoria)
    modelo, clases, _ = Reconocedor()._cargar_modelo(categoria)

    resultado = Counter()
    confusiones = Counter()
    for carpeta, nombre in clips_de_categoria(categoria):
        if partes_de_nombre(nombre)[0] not in PERSONAS_VALIDACION:
            continue
        vistas = palabras_detectadas(modelo, clases, np.load(ruta_crudo(carpeta, nombre)))
        if carpeta in vocab:
            if vistas == [carpeta]:
                resultado["bien"] += 1
            elif not vistas:
                resultado["sin respuesta"] += 1
            else:
                resultado["mal"] += 1
                confusiones[(config.palabra_es(carpeta), tuple(config.palabra_es(v) for v in vistas))] += 1
        else:
            resultado["otra seña: callado" if not vistas else "otra seña: invento una palabra"] += 1

    de_categoria = resultado["bien"] + resultado["mal"] + resultado["sin respuesta"]
    otras = resultado["otra seña: callado"] + resultado["otra seña: invento una palabra"]
    print(f"\nCategoria '{categoria}', simulando la camara con personas {sorted(PERSONAS_VALIDACION)}:")
    print(f"  Señas de la categoria ({de_categoria} clips):")
    for clave in ("bien", "mal", "sin respuesta"):
        print(f"    {clave:14s} {resultado[clave]:3d}  ({100 * resultado[clave] / de_categoria:.0f}%)")
    print(f"  Señas que NO son de la categoria ({otras} clips):")
    print(f"    se queda callado        {resultado['otra seña: callado']:3d}  ({100 * resultado['otra seña: callado'] / otras:.0f}%)")
    print(f"    inventa una palabra     {resultado['otra seña: invento una palabra']:3d}")
    if confusiones:
        print("  Confusiones (seña hecha -> lo que mostro):")
        for (real, vistas), n in confusiones.most_common():
            print(f"    {real} -> {', '.join(vistas)}  x{n}")


if __name__ == "__main__":
    main(sys.argv[1])
