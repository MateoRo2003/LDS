"""
Configuracion compartida por los scripts de app-python/.

CATEGORIAS: el vocabulario esta separado por categoria (colores,
prueba, etc.) en vez de una lista unica. Cada categoria entrena y usa
SU PROPIO modelo (dataset_<categoria>.npz, modelo_<categoria>.keras) —
asi una "interfaz que solo detecta colores" es simplemente correr los
scripts pasando --categoria colores, sin mezclarse con el resto del
vocabulario.

OJO: LSA64 (64 señas) no incluye numeros — no es que falte agregarlos
a la lista, es que esa categoria no existe en el dataset descargado.
Para tener una categoria de numeros hace falta grabarla con
captura-web y organizarla en datos/propio/ igual que lsa64_por_palabra/.
"""
import os

RAIZ = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(RAIZ)

# carpeta con subcarpetas "{id}-{palabra}/" llenas de .mp4 (la que arma
# datos/externos/organizar_lsa64.py). El extractor tambien puede apuntar
# a datos/propio/ el dia que tengan grabaciones propias organizadas asi.
CARPETA_DATASET_LSA64 = os.path.join(PROYECTO, "datos", "externos", "lsa64_por_palabra")

CATEGORIAS = {
    # vocabulario mixto original, usado para validar que el pipeline
    # entero funciona de punta a punta (ver conversacion previa).
    "prueba": [
        "051-thanks",
        "056-help",
        "022-water",
        "021-milk",
        "023-food",
        "059-buy",
        "039-name",
        "057-dance",
    ],
    # las 8 primeras señas de LSA64 son justo la categoria "colores"
    # del dataset original.
    "colores": [
        "001-opaque",
        "002-red",
        "003-green",
        "004-yellow",
        "005-bright",
        "006-light-blue",
        "007-colors",
        "008-pink",
    ],
    # "numeros": no existe en LSA64. Cuando graben numeros propios con
    # captura-web, agregar aca la lista de carpetas correspondiente.
}

# Cuantos frames por clip (resampleados) usa el modelo. Todos los clips
# se estiran/comprimen a esta longitud para tener una entrada de tamaño
# fijo para la LSTM.
LONGITUD_SECUENCIA = 30

# 21 puntos x (x,y,z) x 2 manos
FEATURES_POR_FRAME = 21 * 3 * 2

RUTA_MODELO_LANDMARKER = os.path.join(RAIZ, "hand_landmarker.task")
MODEL_URL_LANDMARKER = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def vocabulario(categoria):
    if categoria not in CATEGORIAS:
        disponibles = ", ".join(CATEGORIAS.keys())
        raise ValueError(f"Categoria '{categoria}' no existe en config.CATEGORIAS. Disponibles: {disponibles}")
    return CATEGORIAS[categoria]


def ruta_dataset(categoria):
    return os.path.join(PROYECTO, "datos", "procesado", f"dataset_{categoria}.npz")


def ruta_modelo(categoria):
    return os.path.join(RAIZ, "modelo", f"modelo_{categoria}.keras")


def ruta_etiquetas(categoria):
    return os.path.join(RAIZ, "modelo", f"etiquetas_{categoria}.json")


def palabra_legible(carpeta):
    """'051-thanks' -> 'thanks' — para mostrar en pantalla, no el id interno."""
    return carpeta.split("-", 1)[1] if "-" in carpeta else carpeta


# Traduccion para pantalla: LSA64 nombra las señas en ingles (asi las
# documento el paper original), pero para la demo en la expo conviene
# mostrar la palabra en español. Si el equipo suma señas propias o mas
# de LSA64, agregar la traduccion correspondiente aca.
TRADUCCION_ES = {
    "thanks": "gracias",
    "help": "ayuda",
    "water": "agua",
    "milk": "leche",
    "food": "comida",
    "buy": "comprar",
    "name": "nombre",
    "dance": "bailar",
    "opaque": "opaco",
    "red": "rojo",
    "green": "verde",
    "yellow": "amarillo",
    "bright": "claro",
    "light-blue": "celeste",
    "colors": "colores",
    "pink": "rosa",
}


def palabra_es(carpeta):
    """'051-thanks' -> 'gracias' — la palabra para mostrar en la demo."""
    en = palabra_legible(carpeta)
    return TRADUCCION_ES.get(en, en)


def asegurar_modelo_landmarker():
    import urllib.request

    if not os.path.exists(RUTA_MODELO_LANDMARKER):
        print("Bajando el modelo de deteccion de manos (una sola vez, ~8MB)...")
        urllib.request.urlretrieve(MODEL_URL_LANDMARKER, RUTA_MODELO_LANDMARKER)
        print("Listo.\n")
