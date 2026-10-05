# Reconocedor de Lengua de Señas Argentina (LSA)

Proyecto para la exposición de Informática: reconocimiento de señas de LSA en vivo por webcam, entrenado con landmarks de mano y cuerpo (MediaPipe) + una red Bi-LSTM.

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

Repetir para `palabras`, o para cualquier categoría nueva que agreguen a `config.py`.

### 4. Correr la app

```bash
python app.py
```

Abre la interfaz (SIGNALIS) con la cámara en vivo; las categorías se eligen y se cambian desde ahí mismo. Más detalle en [app-python/README.md](app-python/README.md).

## Vocabulario actual

32 señas de LSA64: 8 "colores" + 24 "palabras". El "abecedario" (27 letras) y los "números" (0 al 10) salen de videos de personas mostrando cada seña, y se les puede sumar grabaciones hechas desde la propia app. Ver [app-python/README.md](app-python/README.md).

## Estado del proyecto

Ver el resto de los READMEs de cada carpeta para el detalle de cada pieza. En curso: que el equipo cierre su lista definitiva de palabras e investigue vocabulario adicional (fuentes en la conversación con el asistente / carpeta de investigación del equipo).
