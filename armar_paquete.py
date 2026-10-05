"""
Arma SIGNALIS-estudiantes.zip: lo que se le pasa a cada persona del
equipo para que instale la app en su computadora.

Lleva el codigo, los modelos ya entrenados, las muestras del abecedario
y los numeros, y los landmarks de LSA64 ya extraidos (para poder
reentrenar colores y palabras). NO lleva los videos de LSA64 (1.5 GB)
ni los videos de donde salieron las letras: no hacen falta para usar ni
para alimentar la app.

Uso:
    python armar_paquete.py
"""
import os
import zipfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "SIGNALIS-estudiantes.zip")

SUELTOS = ["instalar.bat", "SIGNALIS.bat"]
CARPETAS = [
    "app-python",
    os.path.join("datos", "propio", "estaticas"),
    os.path.join("datos", "procesado", "crudo"),
    "docs",
]
SALTEAR_CARPETAS = {"__pycache__", ".venv"}


def main():
    cuantos = 0
    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in SUELTOS:
            z.write(os.path.join(RAIZ, nombre), os.path.join("SIGNALIS", nombre))
            cuantos += 1
        for carpeta in CARPETAS:
            for actual, subcarpetas, archivos in os.walk(os.path.join(RAIZ, carpeta)):
                subcarpetas[:] = [s for s in subcarpetas if s not in SALTEAR_CARPETAS]
                for archivo in archivos:
                    ruta = os.path.join(actual, archivo)
                    z.write(ruta, os.path.join("SIGNALIS", os.path.relpath(ruta, RAIZ)))
                    cuantos += 1
    print(f"{SALIDA}: {cuantos} archivos, {os.path.getsize(SALIDA) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
