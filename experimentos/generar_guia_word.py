"""
Genera docs/Guia SIGNALIS.docx: la guia para el equipo, con como
instalar y usar la app, y todo el vocabulario con una
imagen de referencia por seña.

Las imagenes salen de los mismos videos con los que se entreno: una
foto por letra y por numero, y tres momentos del movimiento para los
colores y las palabras. Volver a correrlo despues de cambiar el
vocabulario en config.py actualiza el documento.

Uso:
    python generar_guia_word.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app-python"))

import cv2
import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

import config
import senas_desde_videos as videos

SALIDA = os.path.join(config.PROYECTO, "docs", "Guia SIGNALIS.docx")
BORDO = RGBColor(0x8B, 0x2E, 0x36)

# De que video sale la foto de cada categoria estatica, y que parte de
# la imagen se usa (x0, x1, y0, y1 en fracciones).
FOTOS_ESTATICAS = {
    "abecedario": ("bhzaMJw_NbE", (0.22, 0.84, 0.0, 0.84)),
    "numeros": ("gLSSENEOGD4", (0.16, 0.78, 0.0, 0.84)),
}


def jpeg(imagen):
    return io.BytesIO(cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes())


def recortar(frame, x0, x1, y0, y1, ancho):
    alto_f, ancho_f = frame.shape[:2]
    parte = frame[int(y0 * alto_f):int(y1 * alto_f), int(x0 * ancho_f):int(x1 * ancho_f)]
    return cv2.resize(parte, (ancho, int(ancho * parte.shape[0] / parte.shape[1])), interpolation=cv2.INTER_AREA)


def fotos_estaticas(categoria):
    """-> lista de (nombre, imagen): el frame del medio del tramo de cada seña."""
    video_id, recorte = FOTOS_ESTATICAS[categoria]
    cap = cv2.VideoCapture(os.path.join(videos.CARPETA_VIDEOS, video_id + ".mp4"))
    fotos = []
    for sena, (desde, hasta) in videos.VIDEOS[video_id]["senas"].items():
        cap.set(cv2.CAP_PROP_POS_MSEC, (desde + hasta) / 2 * 1000)
        _, frame = cap.read()
        fotos.append((sena, jpeg(recortar(frame, *recorte, 520))))
    return fotos


def fotos_con_movimiento(categoria):
    """-> lista de (nombre, imagen): tres momentos de un clip de LSA64, uno al lado del otro."""
    fotos = []
    for carpeta in config.vocabulario(categoria):
        ruta = os.path.join(config.CARPETA_DATASET_LSA64, carpeta)
        cap = cv2.VideoCapture(os.path.join(ruta, sorted(os.listdir(ruta))[0]))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        momentos = []
        for fraccion in (0.3, 0.5, 0.7):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * fraccion))
            _, frame = cap.read()
            momentos.append(recortar(frame, 0.24, 0.72, 0.04, 0.78, 400))
        fotos.append((config.palabra_es(carpeta), jpeg(np.hstack(momentos))))
    return fotos


def titulo(doc, texto, nivel):
    parrafo = doc.add_heading(texto, level=nivel)
    for tramo in parrafo.runs:
        tramo.font.color.rgb = BORDO
        tramo.font.name = "Segoe UI"
    return parrafo


def pasos(doc, lista):
    for paso in lista:
        doc.add_paragraph(paso, style="List Number")


def puntos(doc, lista):
    for punto in lista:
        doc.add_paragraph(punto, style="List Bullet")


def grilla_de_fotos(doc, fotos, columnas, ancho_cm):
    tabla = doc.add_table(rows=0, cols=columnas)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i in range(0, len(fotos), columnas):
        celdas = tabla.add_row().cells
        for celda, (nombre, imagen) in zip(celdas, fotos[i:i + columnas]):
            parrafo = celda.paragraphs[0]
            parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            parrafo.add_run().add_picture(imagen, width=Cm(ancho_cm))
            pie = celda.add_paragraph()
            pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
            tramo = pie.add_run(nombre.upper())
            tramo.bold = True
            tramo.font.size = Pt(13)
            tramo.font.color.rgb = BORDO


def main():
    doc = Document()
    doc.styles["Normal"].font.name = "Segoe UI"
    doc.styles["Normal"].font.size = Pt(11)
    for seccion in doc.sections:
        seccion.left_margin = seccion.right_margin = Cm(2)
        seccion.top_margin = seccion.bottom_margin = Cm(2)

    titulo(doc, "SIGNALIS", 0)
    doc.add_paragraph("Reconocimiento de Lengua de Señas Argentina. Guía del sistema y su vocabulario.")

    titulo(doc, "Qué es SIGNALIS", 1)
    doc.add_paragraph(
        "SIGNALIS es una aplicación que mira por la cámara de la computadora y reconoce señas de la Lengua de "
        "Señas Argentina (LSA). Muestra en pantalla qué seña vio y con cuánta confianza, y tiene un modo "
        "práctica que dice si la seña que hiciste es la que querías hacer.")
    doc.add_paragraph(
        "Reconoce cuatro categorías: el abecedario, los números del 0 al 10, colores y palabras de uso "
        "cotidiano. Todas están en la última parte de esta guía, con una imagen de cada una.")

    titulo(doc, "Instalación", 1)
    pasos(doc, [
        "Instalá Python desde python.org/downloads (versión 3.11 o más nueva). En la primera pantalla del "
        "instalador marcá la casilla «Add python.exe to PATH».",
        "Descomprimí el archivo SIGNALIS-estudiantes.zip en una carpeta, por ejemplo en el Escritorio.",
        "Dentro de la carpeta SIGNALIS, hacé doble clic en instalar.bat y esperá a que termine. Tarda varios "
        "minutos y necesita internet. Se hace una sola vez.",
        "Para abrir la aplicación, doble clic en SIGNALIS.bat. Para cerrarla, cerrá su ventana.",
    ])

    titulo(doc, "Cómo se usa", 1)
    pasos(doc, [
        "Sentate de frente a la cámara, con buena luz, de modo que se vean la cara, los hombros y las manos.",
        "Elegí una categoría en la barra de la izquierda o en «Explorar categorías».",
        "Hacé la seña. A la derecha aparece la seña detectada y la confianza.",
        "Para practicar una seña puntual, tocala en la lista que aparece debajo de las categorías: la app "
        "te dice si lo que hiciste es esa seña o no.",
    ])
    puntos(doc, [
        "Letras y números: son posturas. Mantené la mano quieta medio segundo.",
        "Colores y palabras: son movimientos. Hacé la seña completa una vez y bajá la mano.",
        "Si hay más de una cámara conectada, se elige arriba a la derecha.",
    ])

    titulo(doc, "Cómo aprendió el sistema", 1)
    doc.add_paragraph(
        "El sistema aprendió las señas a partir de datos públicos: el conjunto LSA64 de la Universidad "
        "Nacional de La Plata para los colores y las palabras, y videos educativos de LSA para el abecedario "
        "y los números.")
    doc.add_paragraph(
        "Una parte del trabajo la hizo el equipo de estudiantes, para pulirlo: probar cada seña frente a la "
        "cámara, registrar cuáles fallaban y con eso ajustar el sistema.")

    titulo(doc, "Vocabulario", 1)
    doc.add_paragraph(
        "Las imágenes muestran a la persona tal como la ve la cámara. En los colores y las palabras, cada "
        "imagen tiene tres momentos del movimiento, de izquierda a derecha.")

    categorias = [
        ("abecedario", "Las 27 letras. Algunas se hacen en un lugar preciso: la frente, la oreja, el mentón.", 3, 5.2),
        ("numeros", "Del 0 al 10.", 3, 5.2),
        ("colores", "Señas con movimiento.", 1, 15.5),
        ("palabras", "Señas con movimiento.", 1, 15.5),
    ]
    for categoria, nota, columnas, ancho in categorias:
        doc.add_page_break()
        titulo(doc, config.INFO_CATEGORIAS[categoria][0], 2)
        doc.add_paragraph(nota)
        fotos = fotos_estaticas(categoria) if categoria in FOTOS_ESTATICAS else fotos_con_movimiento(categoria)
        grilla_de_fotos(doc, fotos, columnas, ancho)

    titulo(doc, "Origen de las imágenes", 2)
    doc.add_paragraph(
        "Abecedario y números: videos «Alfabeto dactilológico LSA» y «Números en LSA» de la Dirección de "
        "Documentación. Colores y palabras: dataset LSA64 de la Universidad Nacional de La Plata "
        "(licencia CC BY-NC-SA).")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    doc.save(SALIDA)
    print(f"{SALIDA}: {os.path.getsize(SALIDA) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
