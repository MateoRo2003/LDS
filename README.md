# SIGNALIS

Aplicación web que reconoce señas de la Lengua de Señas Argentina (LSA) con la cámara: abecedario, números del 0 al 10, colores y palabras.

Este repositorio tiene los archivos listos para subir al campus.

## Cómo subirlo al campus

1. En esta página, tocá el botón verde **Code** y después **Download ZIP**.
2. Descomprimí el archivo. Te queda una carpeta `LDS-main` con todo adentro.
3. En el campus, creá un entorno nuevo y elegí **HTML5 · Vanilla Web**.
4. Subí todos los archivos de la carpeta **menos este `README.md`**, respetando las carpetas:
   - sueltos: `index.html`, `style.css`, `app.js`, `motor.js`
   - dentro de `modelos/`: los 12 archivos `.json`
   - dentro de `vendor/tasks-vision/`: `vision_bundle.js`
5. Tocá **Ejecutar** y después **Visitar sitio**.

Tienen que quedar 17 archivos. Si falta alguno o queda en otra carpeta, la aplicación no carga.

## Estructura de carpetas

Así tiene que verse en el campus, con los mismos nombres y en minúsculas:

```
index.html
style.css
app.js
motor.js
modelos/
├── abecedario.json
├── numeros.json
├── colores.json
├── colores.parte1.json
├── colores.parte2.json
├── colores.parte3.json
├── colores.parte4.json
├── palabras.json
├── palabras.parte1.json
├── palabras.parte2.json
├── palabras.parte3.json
└── palabras.parte4.json
vendor/
└── tasks-vision/
    └── vision_bundle.js
```

Qué es cada cosa:

- `index.html` y `style.css`: la pantalla.
- `app.js`: la cámara y los botones.
- `motor.js`: el reconocimiento de las señas.
- `modelos/`: lo que la inteligencia artificial aprendió, un modelo por categoría. Los de colores y palabras son grandes y van partidos en cuatro archivos.
- `vendor/tasks-vision/`: MediaPipe, la librería que ubica las manos en la imagen. Ojo: es una carpeta dentro de otra.

## Cómo usarla

1. Abrila en Chrome o Edge.
2. Cuando el navegador pregunte, permití el uso de la cámara.
3. Ponete de frente, con la cara, los hombros y las manos a la vista.
4. Elegí una categoría y hacé la seña.

La primera vez tarda un poco en cargar. La imagen de la cámara no sale de tu computadora.

## Si algo no anda

- **Dice «No se pudo cargar el reconocimiento»:** revisá que estén los 17 archivos en sus carpetas y que haya internet.
- **Subiste una versión nueva y se sigue viendo la anterior:** el navegador guarda la página unas horas. Recargá con **Ctrl + Shift + R**, o abrila en una ventana de incógnito.
- **No pide la cámara o dice que no tiene permiso:** tocá el candado de la barra de direcciones, permití la cámara y recargá.
- **Colores o Palabras aparecen apagados:** falta alguno de los archivos `colores.parte…json` o `palabras.parte…json`.
