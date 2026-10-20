"""
Configuracion compartida por los scripts de app-python/.

CATEGORIAS: el vocabulario esta separado por categoria (colores,
palabras, etc.) en vez de una lista unica. Cada categoria entrena y usa
SU PROPIO modelo (modelo_<categoria>.keras) — asi "solo detectar
colores" es simplemente elegir esa categoria en la app, sin mezclarse
con el resto del vocabulario.

OJO: LSA64 (64 señas) no incluye numeros ni abecedario — no es que
falte agregarlos a la lista, es que esas categorias no existen en el
dataset descargado. Para tenerlas hace falta grabarlas con captura-web
y organizarlas en datos/propio/ igual que lsa64_por_palabra/. Mientras
tanto quedan con la lista vacia y la app las muestra como "Proximamente".
"""
import os

RAIZ = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(RAIZ)

# carpeta con subcarpetas "{id}-{palabra}/" llenas de .mp4 (la que arma
# datos/externos/organizar_lsa64.py). El extractor tambien puede apuntar
# a datos/propio/ el dia que tengan grabaciones propias organizadas asi.
CARPETA_DATASET_LSA64 = os.path.join(PROYECTO, "datos", "externos", "lsa64_por_palabra")

# landmarks crudos ya extraidos, un .npz por clip (cache: extraer un
# video tarda varios segundos, asi que se hace una sola vez por clip).
CARPETA_CRUDO = os.path.join(PROYECTO, "datos", "procesado", "crudo")

# El orden de este dict es el orden en que aparecen en la interfaz.
CATEGORIAS = {
    # "abecedario" y "numeros": no existen en LSA64. Cuando graben los
    # propios con captura-web, agregar aca la lista de carpetas.
    "abecedario": [],
    "numeros": [],
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
    # vocabulario mixto de palabras de uso cotidiano.
    "palabras": [
        "051-thanks",
        "056-help",
        "022-water",
        "021-milk",
        "023-food",
        "059-buy",
        "039-name",
        "057-dance",
        "009-women",
        "011-son",
        "016-learn",
        "028-where",
        "030-birthday",
        "031-breakfast",
        "033-hungry",
        "036-music",
        "032-photo",
        "042-deaf",
        "040-patience",
        "050-accept",
        "063-give",
        "024-argentina",
    ],
    # Saludos y preguntas no estan en LSA64 (salvo gracias y donde): salen
    # de videos, con experimentos/palabras_desde_videos.py. En la
    # interfaz son grupos dentro de "palabras" (ver DENTRO_DE).
    "saludos": [
        "101-hola",
        "102-chau",
        "103-buen-dia",
        "104-buenas-tardes",
        "105-buenas-noches",
        "106-hasta-manana",
        "051-thanks",
        "107-muchas-gracias",
        "108-por-favor",
        "109-lo-siento",
        "110-felicitaciones",
        "111-perdon",
        "112-bienvenidos",
    ],
    "preguntas": [
        "121-cuando",
        "122-como",
        "123-cuantos",
        "124-cual",
        "125-cual-de-los-dos",
        "126-quien",
        "127-que",
        "128-por-que",
        "028-where",
    ],
}

# Categorias que en la interfaz aparecen como un grupo dentro de otra.
DENTRO_DE = {"saludos": "palabras", "preguntas": "palabras"}

# Categorias de señas ESTATICAS: se reconocen por la postura en un
# instante, sin movimiento. No salen de LSA64: sus muestras se sacan de
# videos (experimentos/senas_desde_videos.py) y quedan en CARPETA_ESTATICAS.
SENAS_ESTATICAS = {
    "abecedario": list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"),
    "numeros": [str(n) for n in range(11)],
}
CARPETA_ESTATICAS = os.path.join(PROYECTO, "datos", "propio", "estaticas")

# Como se muestra cada categoria en la interfaz: (titulo, tipo de seña).
INFO_CATEGORIAS = {
    "abecedario": ("Abecedario", "Letra"),
    "numeros": ("Números", "Número"),
    "colores": ("Colores", "Color"),
    "palabras": ("Palabras", "Palabra"),
    "saludos": ("Saludos", "Saludo"),
    "preguntas": ("Preguntas", "Pregunta"),
}

# Clase extra que aprende cada modelo: "esto no es ninguna seña de la
# categoria" (mano quieta, otra seña, gesto cualquiera). Sin ella el
# modelo esta obligado a elegir siempre alguna de sus palabras.
CLASE_NADA = "_nada"

# Para la clase "nada" se usan clips de las señas de LSA64 que NO son
# de la categoria: solo esta repeticion de cada persona, para no
# desbalancear el entrenamiento.
REPETICION_NEGATIVOS = 1

# Cuantos frames por clip (resampleados) usa el modelo. Todos los clips
# se estiran/comprimen a esta longitud para tener una entrada de tamaño
# fijo para la LSTM.
LONGITUD_SECUENCIA = 30

# Los videos de LSA64 estan a 60 fps y una webcam da ~30: al extraer se
# saltean frames para quedar cerca de esta cadencia.
FPS_OBJETIVO = 30

# Por mano: 21 puntos x (x,y,z) relativos a la muñeca + posicion de la
# muñeca respecto de la cara (x,y) + 1 si la mano esta presente.
FEATURES_POR_MANO = 21 * 3 + 2 + 1
FEATURES_POR_FRAME = FEATURES_POR_MANO * 2

_URL_MODELOS = "https://storage.googleapis.com/mediapipe-models/"
RUTA_MODELO_LANDMARKER = os.path.join(RAIZ, "hand_landmarker.task")
MODEL_URL_LANDMARKER = _URL_MODELOS + "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
RUTA_MODELO_POSE = os.path.join(RAIZ, "pose_landmarker_lite.task")
MODEL_URL_POSE = _URL_MODELOS + "pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"


def vocabulario(categoria):
    if categoria not in CATEGORIAS:
        disponibles = ", ".join(CATEGORIAS.keys())
        raise ValueError(f"Categoria '{categoria}' no existe en config.CATEGORIAS. Disponibles: {disponibles}")
    return CATEGORIAS[categoria]


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
    "women": "mujer",
    "son": "hijo",
    "learn": "aprender",
    "where": "dónde",
    "birthday": "cumpleaños",
    "breakfast": "desayuno",
    "hungry": "hambre",
    "music": "música",
    "photo": "foto",
    "deaf": "sordo",
    "patience": "paciencia",
    "accept": "aceptar",
    "give": "dar",
    "argentina": "argentina",
    "opaque": "opaco",
    "red": "rojo",
    "green": "verde",
    "yellow": "amarillo",
    "bright": "claro",
    "light-blue": "celeste",
    "colors": "colores",
    "pink": "rosa",
    # las señas que salen de videos ya tienen nombre en español: aca solo
    # van las que llevan tilde o espacios
    "buen-dia": "buen día",
    "buenas-tardes": "buenas tardes",
    "buenas-noches": "buenas noches",
    "hasta-manana": "hasta mañana",
    "muchas-gracias": "muchas gracias",
    "por-favor": "por favor",
    "lo-siento": "lo siento",
    "perdon": "perdón",
    "cuando": "cuándo",
    "como": "cómo",
    "cuantos": "cuántos",
    "cual": "cuál",
    "cual-de-los-dos": "cuál de los dos",
    "quien": "quién",
    "que": "qué",
    "por-que": "por qué",
}


def palabra_es(carpeta):
    """'051-thanks' -> 'gracias' — la palabra para mostrar en la demo."""
    en = palabra_legible(carpeta)
    return TRADUCCION_ES.get(en, en)


def _asegurar(ruta, url, descripcion):
    import urllib.request

    if not os.path.exists(ruta):
        print(f"Bajando el modelo de {descripcion} (una sola vez, ~8MB)...")
        urllib.request.urlretrieve(url, ruta)
        print("Listo.\n")


def asegurar_modelo_landmarker():
    _asegurar(RUTA_MODELO_LANDMARKER, MODEL_URL_LANDMARKER, "deteccion de manos")


def asegurar_modelo_pose():
    _asegurar(RUTA_MODELO_POSE, MODEL_URL_POSE, "deteccion de cuerpo")
