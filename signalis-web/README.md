# SIGNALIS, versión web

La misma aplicación que `app-python/`, pero corre entera en el navegador: se abre un enlace, se permite la cámara y listo, sin instalar nada. La imagen de la cámara no se envía a ningún lado; todo el reconocimiento se hace en la computadora de quien la abre.

Es un sitio estático (HTML, CSS y JavaScript, sin servidor propio ni paso de compilación), así que se puede publicar en cualquier hosting de archivos.

## Probarla en esta computadora

```bash
python servidor_local.py
```

y abrir http://127.0.0.1:8790/ en Chrome o Edge. El navegador solo deja usar la cámara desde `https` o desde la propia máquina, por eso no alcanza con abrir `index.html` con doble clic.

## Publicarla

Desde esta carpeta, con la herramienta de Vercel (la primera vez pide iniciar sesión):

```bash
npx vercel deploy --prod
```

`.vercelignore` deja afuera lo que es solo para probar.

## Cómo está hecha

- `index.html`, `style.css`, `app.js` — la interfaz, la cámara y el dibujo de la mano.
- `motor.js` — el reconocimiento: las mismas cuentas que hace Python (`landmarks.py`, `reconocedor.py`, `estaticas.py`), escritas en JavaScript y sin librerías. Incluye el cálculo de las redes neuronales.
- `modelos/` — los cuatro modelos de SIGNALIS (un `.json` por categoría) y los dos de MediaPipe que ubican manos y cuerpo.
- `vendor/tasks-vision/` — MediaPipe para navegador, versión 1.0.1 (la misma que usa Python), copiado acá para no depender de otro sitio.

## Después de reentrenar un modelo

Los modelos se entrenan en Python, como siempre. Para pasarlos a la web:

```bash
cd ../app-python
python exportar_web.py
cd ../signalis-web
node verificar.mjs
```

`exportar_web.py` escribe los `.json` de `modelos/` y, en `pruebas/casos.json`, casos calculados con Python. `verificar.mjs` hace las mismas cuentas con `motor.js` y comprueba que den lo mismo: las características, las probabilidades y las señas detectadas en vivo. Si todo coincide, se vuelve a publicar.

## Probar sin cámara

`?video=<archivo>&cat=<categoria>` recorre un video imagen por imagen en lugar de usar la cámara, por ejemplo `http://127.0.0.1:8790/?video=pruebas/rojo.mp4&cat=colores`. El resultado queda en el historial de la página.
