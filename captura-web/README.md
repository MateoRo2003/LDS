# Captura de señas — herramienta web

Página que graba los clips del dataset. No necesita instalación: se abre el link en cualquier navegador (celular o notebook), se pide permiso de cámara, y graba.

## Antes de la sesión de grabación grupal

Editar `script.js`, arriba de todo, el bloque `CONFIG`:

- `palabras`: reemplazar por la lista final del equipo.
- `repeticionesPorPalabra`: 10 por defecto (según lo charlado, 6 personas × 10 = 60 clips por palabra).
- `duracionClipMs`: 3000 (3 segundos) suele alcanzar; ajustar si alguna seña es más larga.

## Deploy a Vercel

Sin build, es HTML/CSS/JS puro. Dos formas:

1. **Sin cuenta ni CLI**: entrar a [vercel.com/new](https://vercel.com/new), arrastrar esta carpeta (`captura-web`) a la página. Da un link al toque.
2. **Con CLI** (si alguien tiene Node instalado): desde esta carpeta, `npx vercel --prod`.

Cualquiera de las dos da una URL tipo `https://algo.vercel.app` — ese es el link que se comparte con el equipo.

## Uso (para cada integrante)

1. Abrir el link en el celular o notebook.
2. Escribir el nombre y tocar **Empezar**.
3. Aceptar el permiso de cámara.
4. Por cada palabra: tocar **Grabar**, esperar la cuenta regresiva, hacer la seña durante la grabación.
5. Mirar el clip: **Guardar y siguiente** si salió bien, **Repetir** si no.
6. Al terminar, los clips quedan en la carpeta de Descargas del dispositivo — subirlos a la carpeta compartida del equipo (Drive) para juntarlos con los del resto.

En notebook se puede usar la barra espaciadora en vez de tocar los botones (graba / guarda y sigue), va más rápido.

## Nombres de archivo

Cada clip se guarda como `{número}_{palabra}_{nombre}_rep{repetición}.webm` (o `.mp4` en Safari), ya ordenado y etiquetado — no hace falta renombrar nada a mano después.
