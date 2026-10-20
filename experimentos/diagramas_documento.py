"""
Dibuja los dos diagramas del documento del proyecto (arquitectura y flujo
de uso) en docs/figuras/. Los usa generar_documento_proyecto.py.

Uso:
    python diagramas_documento.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

import config

CARPETA = os.path.join(config.PROYECTO, "docs", "figuras")
BORDO = "#8b2e36"
ROSA = "#f6eceb"
GRIS = "#ececec"
GRIS_BORDE = "#444444"
AZUL = "#2f5d8a"
CELESTE = "#e7eef6"
AMARILLO = "#fdf5e1"
OCRE = "#b8862e"
TEXTO = "#1a1a1a"


def caja(ax, x, y, w, h, texto, fondo, borde, tam=9.5, negrita=False, estilo="-", redondeo=0.08, color=TEXTO):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={redondeo}",
                                facecolor=fondo, edgecolor=borde, linewidth=1.6, linestyle=estilo))
    if texto:
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=tam, color=color,
                fontweight="bold" if negrita else "normal", linespacing=1.25)


def flecha(ax, x0, y0, x1, y1, doble=False):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<|-|>" if doble else "-|>", color=GRIS_BORDE, lw=1.6,
                                shrinkA=0, shrinkB=0, mutation_scale=12))


def lienzo(ancho, alto):
    fig, ax = plt.subplots(figsize=(ancho, alto), dpi=150)
    ax.set_xlim(0, ancho)
    ax.set_ylim(0, alto)
    ax.axis("off")
    return fig, ax


def arquitectura():
    fig, ax = lienzo(9.0, 6.4)
    # navegador
    caja(ax, 2.15, 0.3, 4.7, 5.85, "", "#fafafa", AZUL, estilo="--", redondeo=0.1)
    ax.text(4.5, 5.85, "Navegador (Chrome o Edge)", ha="center", va="center", fontsize=12.5,
            color=AZUL, fontweight="bold")
    caja(ax, 2.4, 4.6, 4.2, 0.95, "Interfaz\nindex.html + style.css\nCategorías, grupos de palabras, lista de\n"
         "señas, seña detectada y confianza", ROSA, BORDO, tam=9)
    caja(ax, 2.4, 3.55, 4.2, 0.72, "Control\napp.js\nManejo de la cámara y de los botones", ROSA, BORDO, tam=9)
    flecha(ax, 4.5, 4.27, 4.5, 4.6, doble=True)
    # reconocimiento
    caja(ax, 2.4, 1.75, 4.2, 1.5, "", "#fafafa", GRIS_BORDE, estilo=":", redondeo=0.04)
    ax.text(4.5, 3.07, "Reconocimiento", ha="center", va="center", fontsize=9, style="italic", color="#555")
    caja(ax, 2.55, 1.9, 1.9, 1.0, "MediaPipe Tasks\nVision\nvision_bundle.js\nUbica las manos", CELESTE, AZUL, tam=8.3)
    caja(ax, 4.65, 1.9, 1.8, 1.0, "motor.js\nIdentifica la seña", ROSA, BORDO, tam=9)
    flecha(ax, 4.45, 2.4, 4.65, 2.4)
    flecha(ax, 4.5, 3.25, 4.5, 3.55, doble=True)
    caja(ax, 2.4, 0.5, 4.2, 0.95, "Modelos (modelos/*.json)\nabecedario · números · colores · palabras\n"
         "(básicas · saludos · preguntas)", GRIS, GRIS_BORDE, tam=9)
    flecha(ax, 5.55, 1.45, 5.55, 1.9, doble=True)
    # afuera del navegador
    caja(ax, 0.15, 4.75, 1.65, 0.8, "Persona usuaria\nhace la seña", GRIS, GRIS_BORDE, tam=9)
    caja(ax, 0.15, 3.25, 1.65, 0.8, "Cámara web", GRIS, GRIS_BORDE, tam=10.5, negrita=True)
    flecha(ax, 0.975, 4.75, 0.975, 4.05)
    flecha(ax, 1.8, 3.65, 2.4, 3.91)
    ax.text(0.975, 2.5, "La imagen de la cámara\nno sale de la\ncomputadora", ha="center", va="center",
            fontsize=8.5, style="italic", color=BORDO)
    caja(ax, 7.2, 2.6, 1.65, 1.5, "Hosting estático\nentorno del\ncampus\n(27 archivos)", GRIS, GRIS_BORDE, tam=9)
    flecha(ax, 7.2, 3.35, 6.85, 3.35)
    return fig


def flujo():
    fig, ax = lienzo(8.6, 8.4)
    cx = 2.75

    def paso(y, texto):
        caja(ax, cx - 2.0, y, 4.0, 0.6, texto, ROSA, BORDO, tam=9)

    caja(ax, cx - 1.25, 7.65, 2.5, 0.5, "Inicio", BORDO, BORDO, tam=11, negrita=True, redondeo=0.25, color="white")
    pasos = ["Abrir SIGNALIS en el campus, con\nChrome o Edge",
             "Permitir el uso de la cámara cuando el\nnavegador lo pregunte",
             "Se cargan el reconocimiento y los modelos\n(la primera vez tarda más)",
             "Elegir una categoría en la barra izquierda\no en «Explorar categorías»",
             "En Palabras, elegir el grupo:\nBásicas, Saludos o Preguntas"]
    y = 6.85
    flecha(ax, cx, 7.65, cx, y + 0.6)
    for i, texto in enumerate(pasos):
        paso(y, texto)
        if i < len(pasos) - 1:
            flecha(ax, cx, y, cx, y - 0.2)
        y -= 0.8
    # decision
    yd = y + 0.8 - 0.25 - 0.55
    flecha(ax, cx, y + 0.8, cx, yd + 0.5)
    ax.add_patch(Polygon([(cx, yd + 0.5), (cx + 1.5, yd), (cx, yd - 0.5), (cx - 1.5, yd)], closed=True,
                         facecolor=AMARILLO, edgecolor=OCRE, linewidth=1.6))
    ax.text(cx, yd, "¿Practicar una\nseña puntual?", ha="center", va="center", fontsize=9)
    xn, xs = 1.25, 4.25
    ax.plot([cx - 1.5, xn], [yd, yd], color=GRIS_BORDE, lw=1.6)
    ax.plot([cx + 1.5, xs], [yd, yd], color=GRIS_BORDE, lw=1.6)
    ax.text(xn + 0.12, yd - 0.35, "No", fontsize=9, style="italic", color="#555")
    ax.text(xs + 0.12, yd - 0.35, "Sí", fontsize=9, style="italic", color="#555")
    y1 = yd - 1.25
    flecha(ax, xn, yd, xn, y1 + 0.7)
    caja(ax, xn - 1.15, y1, 2.3, 0.7, "Hacer la seña frente\na la cámara", ROSA, BORDO, tam=9)
    flecha(ax, xn, y1, xn, y1 - 0.3)
    caja(ax, xn - 1.15, y1 - 1.0, 2.3, 0.7, "Se muestra la seña\ndetectada y la confianza", CELESTE, AZUL, tam=9)
    flecha(ax, xs, yd, xs, y1 + 0.7)
    caja(ax, xs - 1.15, y1, 2.3, 0.7, "Tocar la seña en la lista\ndebajo de las categorías", ROSA, BORDO, tam=9)
    flecha(ax, xs, y1, xs, y1 - 0.25)
    caja(ax, xs - 1.15, y1 - 0.85, 2.3, 0.6, "Hacer la seña frente\na la cámara", ROSA, BORDO, tam=9)
    flecha(ax, xs, y1 - 0.85, xs, y1 - 1.1)
    caja(ax, xs - 1.15, y1 - 1.7, 2.3, 0.6, "La app indica si es esa\nseña o no", CELESTE, AZUL, tam=9)
    # notas
    caja(ax, 5.95, 4.55, 2.5, 2.05, "Tipos de seña\nLetras y números: son\nposturas; mantener la\nmano quieta medio "
         "segundo.\nColores y palabras: son\nmovimientos; hacer la\nseña completa una vez\ny bajar la mano.",
         GRIS, GRIS_BORDE, tam=8.3)
    caja(ax, 5.95, y1 - 0.9, 2.5, 1.25, "Para repetir\nSe puede cambiar de\ncategoría, de grupo o de\n"
         "seña en cualquier momento.", GRIS, GRIS_BORDE, tam=8.3)
    ax.set_ylim(y1 - 1.85, 8.25)
    return fig


def main():
    os.makedirs(CARPETA, exist_ok=True)
    for nombre, figura in (("arquitectura.png", arquitectura()), ("flujo_de_uso.png", flujo())):
        figura.savefig(os.path.join(CARPETA, nombre), bbox_inches="tight", facecolor="white")
        plt.close(figura)
        print(os.path.join(CARPETA, nombre))


if __name__ == "__main__":
    main()
