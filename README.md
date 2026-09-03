# Reconocedor de Lengua de Señas Argentina (LSA)

Proyecto para la exposición de Informática: reconocimiento de señas de LSA en vivo por webcam, entrenado con landmarks de mano (MediaPipe) + una red Bi-LSTM.

## Estructura

```
app-python/       app de escritorio: entrenamiento + reconocimiento en vivo (lo que se muestra en la expo)
captura-web/       herramienta web para que el equipo grabe sus propias señas, sin instalar nada
datos/             datasets (externos y propios), separados de los .py
experimentos/       scripts sueltos de prueba y verificación
```

## Cómo correrlo

### 1. Instalar dependencias

```bash
cd app-python
pip install -r requirements.txt
```

### 2. Conseguir los datos

Este repo **no incluye el dataset** (LSA64 pesa ~1.5GB, está afuera de git — ver `.gitignore`). Para reconstruirlo:

1. Bajar la versión "cut" de [LSA64](https://facundoq.github.io/datasets/lsa64/) y descomprimirla en cualquier carpeta.
2. Organizarla por palabra:
   ```bash
   python datos/externos/organizar_lsa64.py <carpeta_descomprimida> datos/externos/lsa64_por_palabra
   ```
3. (Opcional) Grabar señas propias del equipo con [captura-web](captura-web/README.md) y organizarlas del mismo modo en `datos/propio/`.

### 3. Entrenar cada categoría

El vocabulario está separado por categoría (ver `app-python/config.py` → `CATEGORIAS`). Por cada una:

```bash
cd app-python
python extraer_landmarks.py --categoria colores
python entrenar_modelo.py --categoria colores
```

Repetir para `prueba`, o para cualquier categoría nueva que agreguen a `config.py`.

### 4. Correr la app

```bash
python app.py
```

Abre un menú con un botón por cada categoría ya entrenada — se elige una, se abre la cámara y reconoce en vivo. Más detalle en [app-python/README.md](app-python/README.md).

## Vocabulario actual

16 señas (8 "prueba" + 8 "colores"), todas del dataset LSA64 — el equipo todavía no grabó ni eligió su propia lista final.

## Estado del proyecto

Ver el resto de los READMEs de cada carpeta para el detalle de cada pieza. En curso: que el equipo cierre su lista definitiva de palabras e investigue vocabulario adicional (fuentes en la conversación con el asistente / carpeta de investigación del equipo).
