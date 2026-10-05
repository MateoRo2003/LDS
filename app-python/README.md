# App de reconocimiento — Python

## Para la expo: un solo comando

```bash
python app.py
```

Abre SIGNALIS en una ventana propia: la cámara en vivo, las categorías, la seña detectada con su confianza y el historial. La categoría se elige (y se cambia) desde la barra de la izquierda o desde las tarjetas de "Explorar categorías", sin cerrar nada; "Inicio" vuelve a dejar ninguna elegida. Al elegir una categoría aparecen sus señas: tocando una se entra en modo práctica y la app dice si la seña que se hizo es esa o no.

Para cerrar, se cierra la ventana (o `Ctrl+C` en la consola).

La interfaz es una página (`web/`) que sirve el propio `app.py` en la misma máquina: no usa internet y no hay que instalar nada aparte de `requirements.txt`.

## Para el equipo: preparar cada categoría (una vez, antes de la expo)

Esto sí es por consola, pero lo corre el equipo al armar el proyecto, no un visitante:

```bash
pip install -r requirements.txt
python extraer_landmarks.py --categoria colores
python entrenar_modelo.py --categoria colores
```

Repetir esos dos últimos pasos por cada categoría nueva. Después de eso, esa categoría se habilita sola en la app.

- El vocabulario de cada categoría vive en `CATEGORIAS` dentro de [config.py](config.py).

## Abecedario y números

LSA64 no tiene letras ni números y no hay ningún dataset público de LSA que los tenga.

Las dos categorías salen de videos donde una persona muestra cada seña (ver [experimentos/senas_desde_videos.py](../experimentos/senas_desde_videos.py), que los extrae y entrena; ahí está de dónde salió cada video):

- **Abecedario**: 27 letras (sin CH ni LL), de 3 personas. Dejando afuera a una persona y probando con ella, reconoce entre 18 y 22 de las 27.
- **Números**: del 0 al 10, de 2 personas. Con la persona que queda afuera reconoce 9 de 11.

Son pocas personas de ejemplo. Para mejorar una categoría hay que sumar videos de otras personas en `experimentos/senas_desde_videos.py` y volver a correrlo.

## Instalarla en otra computadora

`python armar_paquete.py` (en la raíz del proyecto) arma `SIGNALIS-estudiantes.zip` con todo lo necesario salvo los videos. En la otra computadora: instalar Python 3.11 o más nuevo, descomprimir, doble clic en `instalar.bat` (una sola vez, necesita internet) y después en `SIGNALIS.bat` para abrirla. La guía para el equipo, con el vocabulario y sus imágenes, está en `docs/Guia SIGNALIS.docx` y se regenera con `python experimentos/generar_guia_word.py`.

## Cómo reconoce

1. MediaPipe ubica en cada imagen los 21 puntos de cada mano, y la nariz y los hombros de la persona.
2. De ahí se calcula lo que ve el modelo: la **forma** de la mano (sin importar su tamaño) y **dónde está respecto de la cara**, medido en anchos de hombros. Por eso da lo mismo estar parado lejos de la cámara, como en los videos de LSA64, o sentado cerca de la notebook.
3. Una red Bi-LSTM mira el último segundo o dos de movimiento y elige entre las señas de la categoría o "nada". Esa clase "nada" se entrena con manos quietas y con señas de otras categorías, para que la app se quede callada en vez de arriesgar una palabra.

Para que funcione, la persona tiene que estar de frente, con la cara y las manos a la vista.

## Archivos

- `app.py` — **el lanzador que se usa en la expo.** Abre la ventana y atiende a la interfaz.
- `web/` — la interfaz (HTML, CSS y JavaScript).
- `reconocedor.py` — el reconocimiento en vivo: lee la cámara, corre MediaPipe y decide qué seña se hizo.
- `estaticas.py` — abecedario y números: sus muestras, el entrenamiento de su modelo y el reconocimiento.
- `config.py` — categorías, vocabularios, rutas, traducciones al español, hiperparámetros.
- `landmarks.py` — funciones compartidas de MediaPipe y el cálculo de lo que ve el modelo. Usa la API nueva de MediaPipe (`mediapipe.tasks`), no la vieja `mp.solutions` que ya no existe.
- `extraer_landmarks.py --categoria X` — videos → landmarks (en `datos/procesado/crudo/`, se hace una sola vez por video).
- `entrenar_modelo.py --categoria X` — landmarks → modelo entrenado para esa categoría.

Para probar el reconocimiento en vivo sin cámara, con clips de personas que el modelo nunca vio: `python ../experimentos/smoke_test_reconocimiento.py colores`.
