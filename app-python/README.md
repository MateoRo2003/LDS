# App de reconocimiento — Python

## Para la expo: un solo comando

```bash
python app.py
```

Abre un menú con un botón por cada categoría ya entrenada (colores, prueba, etc.). Se elige una, se abre la cámara y reconoce en vivo; al apretar `q` en la ventana de la cámara, vuelve al menú para probar otra categoría. Nada de tipear comandos ni parámetros — esto es lo único que corre alguien en la mesa de la expo.

## Para el equipo: preparar cada categoría (una vez, antes de la expo)

Esto sí es por consola, pero lo corre el equipo al armar el proyecto, no un visitante:

```bash
pip install -r requirements.txt
python extraer_landmarks.py --categoria colores
python entrenar_modelo.py --categoria colores
```

Repetir esos dos últimos pasos por cada categoría nueva. Después de eso, esa categoría ya aparece sola como botón en `app.py`.

- El vocabulario de cada categoría vive en `CATEGORIAS` dentro de [config.py](config.py). Para sumar una categoría nueva (ej. "numeros"), agregar ahí la lista de carpetas de palabras y correr los dos comandos de arriba con `--categoria numeros`.
- **"números" no existe todavía**: LSA64 no tiene señas numéricas — hay que grabarlas con [captura-web](../captura-web/) y organizarlas en `datos/propio/` igual que están organizadas las de LSA64 (ver [datos/externos/organizar_lsa64.py](../datos/externos/organizar_lsa64.py) como referencia del formato de carpetas).

## Archivos

- `app.py` — **el lanzador que se usa en la expo.** Menú con botones, uno por categoría entrenada.
- `config.py` — categorías, vocabularios, rutas, traducciones al español, hiperparámetros.
- `landmarks.py` — funciones compartidas de MediaPipe (extraer features, dibujar esqueleto, resamplear secuencias). Usa la API nueva de MediaPipe (`mediapipe.tasks`), no la vieja `mp.solutions` que ya no existe.
- `extraer_landmarks.py --categoria X` — video → dataset de secuencias de landmarks para esa categoría.
- `entrenar_modelo.py --categoria X` — dataset → modelo entrenado para esa categoría.
- `reconocer_en_vivo.py --categoria X` — el reconocimiento en sí (usado tanto desde `app.py` como solo, por consola, si hace falta debuggear).
