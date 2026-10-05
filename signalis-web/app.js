// SIGNALIS, version web. Todo corre en el navegador de quien la abre:
// MediaPipe ubica las manos y el cuerpo en la imagen de la camara,
// motor.js decide que seña es, y esta pagina lo muestra. La imagen de la
// camara no se envia a ningun lado.

import { FilesetResolver, HandLandmarker, PoseLandmarker } from './vendor/tasks-vision/vision_bundle.js';
import { Modelo, crearSeguidor } from './motor.js';

const CATEGORIAS = ['abecedario', 'numeros', 'colores', 'palabras'];
const PUNTOS_CUERPO = [0, 11, 12];   // nariz y los dos hombros, en el modelo de pose
const HISTORIAL_CORTO = 3;
const ICONO_MANO = 'M12.5 2C11.1 2 10 3.1 10 4.5V11H8.5C7.1 11 6 12.1 6 13.5V19C6 20.7 7.3 22 9 22H15C16.7 22 18 20.7 18 19V4.5C18 3.1 16.9 2 15.5 2H12.5Z';
// que puntos de la mano se unen con una linea al dibujarla
const HUESOS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];

const $ = (id) => document.getElementById(id);
const video = $('video');
const lienzo = $('lienzo');
const pincel = lienzo.getContext('2d');

// Para probar sin camara: ?video=pruebas/clip.mp4 usa ese archivo en su lugar.
const parametros = new URLSearchParams(location.search);
const VIDEO_DE_PRUEBA = parametros.get('video');

const modelos = {};            // id de categoria -> Modelo
let detectorManos = null;
let detectorCuerpo = null;
let seguidor = null;
let ultimoTiempo = -1;

const estado = {
  fase: 'cargando',            // 'cargando', 'sin_camara' o 'listo'
  mensaje: 'Cargando el reconocimiento…',
  categoria: parametros.get('cat'),
  mano: false,
  cuerpo: false,
  palabra: null,
  confianza: 0,
  historial: [],
  ajustes: { umbral: 0.6, esqueleto: true, espejo: true },
  camaras: [],
  camara: null,
};
window.signalis = estado;      // para mirar el estado desde la consola del navegador

let vista = 'inicio';          // 'inicio' o 'ajustes'
let objetivo = null;           // seña que se esta practicando
let resultadoPractica = null;  // { bien, palabra } de la ultima seña hecha
let historialCompleto = false;
let senasDibujadas = null;
let camarasDibujadas = '';

function recordar(clave, valor) {
  try { localStorage.setItem(clave, valor); } catch (e) { /* sin almacenamiento: no pasa nada */ }
}

function recordado(clave) {
  try { return localStorage.getItem(clave); } catch (e) { return null; }
}

// ---------------------------------------------------------------------
// Reconocimiento
// ---------------------------------------------------------------------

async function cargarModelos() {
  await Promise.all(CATEGORIAS.map(async (id) => {
    try {
      const respuesta = await fetch(`modelos/${id}.json`);
      if (respuesta.ok) modelos[id] = new Modelo(await respuesta.json());
    } catch (e) { /* esa categoria queda como "Proximamente" */ }
  }));
  if (!modelos[estado.categoria]) estado.categoria = null;
}

async function crearDetectores() {
  const archivos = await FilesetResolver.forVisionTasks('vendor/tasks-vision/wasm');
  // Primero con la placa de video, que es mas rapido; si no se puede, con el procesador.
  for (const delegate of ['GPU', 'CPU']) {
    try {
      detectorManos = await HandLandmarker.createFromOptions(archivos, {
        baseOptions: { modelAssetPath: 'modelos/hand_landmarker.task', delegate },
        runningMode: 'VIDEO', numHands: 2,
        minHandDetectionConfidence: 0.5, minTrackingConfidence: 0.5,
      });
      detectorCuerpo = await PoseLandmarker.createFromOptions(archivos, {
        baseOptions: { modelAssetPath: 'modelos/pose_landmarker_lite.task', delegate },
        runningMode: 'VIDEO',
      });
      return;
    } catch (e) {
      if (delegate === 'CPU') throw e;
    }
  }
}

// Lo que MediaPipe vio en un instante, en el formato que espera motor.js.
// Las manos van ordenadas por lado ("Left", "Right"), no por orden de
// deteccion, para que no salten de lugar de un instante al otro.
function armarFrame(manosVistas, cuerpoVisto) {
  const vacia = () => Array.from({ length: 21 }, () => [0, 0, 0]);
  const frame = { manos: [vacia(), vacia()], presente: [false, false], cuerpo: [[0, 0], [0, 0], [0, 0]], cuerpo_ok: false };
  const lados = manosVistas.handedness || manosVistas.handednesses || [];
  manosVistas.landmarks.forEach((puntos, i) => {
    const h = lados[i] && lados[i][0].categoryName === 'Left' ? 0 : 1;
    frame.manos[h] = puntos.map((p) => [p.x, p.y, p.z]);
    frame.presente[h] = true;
  });
  const cuerpo = cuerpoVisto.landmarks && cuerpoVisto.landmarks[0];
  if (cuerpo) {
    frame.cuerpo = PUNTOS_CUERPO.map((i) => [cuerpo[i].x, cuerpo[i].y]);
    frame.cuerpo_ok = true;
  }
  return frame;
}

function dibujarManos(manosVistas) {
  if (lienzo.width !== video.videoWidth) {
    lienzo.width = video.videoWidth;
    lienzo.height = video.videoHeight;
  }
  pincel.clearRect(0, 0, lienzo.width, lienzo.height);
  if (!estado.ajustes.esqueleto) return;
  const grosor = Math.max(2, lienzo.width / 320);
  for (const puntos of manosVistas.landmarks) {
    const x = (p) => p.x * lienzo.width;
    const y = (p) => p.y * lienzo.height;
    pincel.strokeStyle = 'rgba(255, 255, 255, 0.85)';
    pincel.lineWidth = grosor;
    pincel.beginPath();
    for (const [a, b] of HUESOS) {
      pincel.moveTo(x(puntos[a]), y(puntos[a]));
      pincel.lineTo(x(puntos[b]), y(puntos[b]));
    }
    pincel.stroke();
    pincel.fillStyle = '#c62828';
    for (const p of puntos) {
      pincel.beginPath();
      pincel.arc(x(p), y(p), grosor * 1.4, 0, 2 * Math.PI);
      pincel.fill();
    }
  }
}

function procesarImagen(ahora) {
  if (video.readyState < 2 || !video.videoWidth) return;
  if (ahora <= ultimoTiempo) return;   // MediaPipe exige tiempos crecientes
  ultimoTiempo = ahora;

  const manosVistas = detectorManos.detectForVideo(video, ahora);
  const cuerpoVisto = detectorCuerpo.detectForVideo(video, ahora);
  const frame = armarFrame(manosVistas, cuerpoVisto);
  dibujarManos(manosVistas);

  estado.fase = 'listo';
  estado.mano = frame.presente[0] || frame.presente[1];
  estado.cuerpo = frame.cuerpo_ok;

  const modelo = modelos[estado.categoria];
  if (!modelo) {
    seguidor = null;
    estado.palabra = null;
    estado.confianza = 0;
    return;
  }
  if (!seguidor || seguidor.modelo !== modelo) seguidor = crearSeguidor(modelo, video.videoWidth / video.videoHeight);

  seguidor.procesar(ahora / 1000, frame, estado.ajustes.umbral);
  estado.confianza = seguidor.confianza;
  estado.palabra = null;
  if (seguidor.detectada) {
    estado.palabra = modelo.nombres[seguidor.detectada.idx];
    estado.confianza = seguidor.detectada.confianza;
    if (seguidor.nueva) alDetectar(estado.palabra, modelo.tipoSena, seguidor.detectada.confianza);
  }
}

function alDetectar(palabra, tipo, confianza) {
  estado.historial.push({ palabra, tipo, confianza, hora: Date.now() });
  if (estado.historial.length > 30) estado.historial.shift();
  if (objetivo) resultadoPractica = { bien: palabra === objetivo, palabra };
  dibujar();
}

// Una vuelta por cada imagen nueva de la camara.
function bucle() {
  try {
    procesarImagen(performance.now());
  } catch (e) {
    console.error(e);
  }
  if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(bucle);
  else requestAnimationFrame(bucle);
}

// ---------------------------------------------------------------------
// Camara
// ---------------------------------------------------------------------

function sinCamara(mensaje, conBoton = true) {
  estado.fase = 'sin_camara';
  estado.mensaje = mensaje;
  $('boton-camara').hidden = !conBoton;
  dibujar();
}

// El navegador puede negarse a reproducir (por ejemplo, con la pestaña
// en segundo plano). No es grave: se reintenta cuando la pestaña vuelve.
function reproducir() {
  return video.play().catch(() => {});
}
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && video.paused && video.srcObject) reproducir();
});

// Modo de prueba: en vez de la camara, recorre un video imagen por imagen
// (a 30 por segundo) y le pasa cada una al reconocimiento.
async function recorrerVideoDePrueba() {
  // se baja entero primero: asi se puede saltar a cualquier instante
  video.src = URL.createObjectURL(await (await fetch(VIDEO_DE_PRUEBA)).blob());
  await new Promise((listo) => video.addEventListener('loadeddata', listo, { once: true }));
  for (let t = 0; t < video.duration; t += 1 / 30) {
    video.currentTime = t;
    await new Promise((listo) => video.addEventListener('seeked', listo, { once: true }));
    procesarImagen(1 + t * 1000);
  }
  estado.pruebaTerminada = true;
  dibujar();
}

async function abrirCamara(idCamara) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    sinCamara('Este navegador no deja usar la cámara desde esta dirección. Abrí la página con https.', false);
    return;
  }
  if (video.srcObject) video.srcObject.getTracks().forEach((pista) => pista.stop());
  const pedido = { width: { ideal: 1280 }, height: { ideal: 720 } };
  if (idCamara) pedido.deviceId = { exact: idCamara };
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({ video: pedido, audio: false });
  } catch (e) {
    if (idCamara && (e.name === 'OverconstrainedError' || e.name === 'NotFoundError')) {
      return abrirCamara(null);   // la camara recordada ya no esta: se usa la que haya
    }
    const mensajes = {
      NotAllowedError: 'El navegador no tiene permiso para usar la cámara. Tocá el candado de la barra de direcciones, permití la cámara y volvé a intentar.',
      NotFoundError: 'No encontré ninguna cámara conectada.',
      NotReadableError: 'No pude abrir la cámara. Revisá que no la esté usando otro programa.',
    };
    return sinCamara(mensajes[e.name] || `No pude abrir la cámara (${e.name}).`);
  }
  await reproducir();
  seguidor = null;   // otra camara: se empieza de cero
  estado.fase = 'listo';
  estado.camara = video.srcObject.getVideoTracks()[0].getSettings().deviceId || null;
  if (estado.camara) recordar('camara', estado.camara);
  // los nombres de las camaras recien se pueden leer despues de dar permiso
  const dispositivos = await navigator.mediaDevices.enumerateDevices();
  estado.camaras = dispositivos.filter((d) => d.kind === 'videoinput')
    .map((d, i) => ({ id: d.deviceId, nombre: d.label || `Cámara ${i + 1}` }));
  dibujar();
}

$('boton-camara').addEventListener('click', () => {
  estado.fase = 'cargando';
  estado.mensaje = 'Abriendo la cámara…';
  $('boton-camara').hidden = true;
  dibujar();
  abrirCamara(recordado('camara'));
});

$('selector-camara').addEventListener('change', (e) => abrirCamara(e.target.value));

function dibujarCamaras() {
  const selector = $('selector-camara');
  selector.parentElement.hidden = estado.camaras.length < 2;
  const clave = estado.camaras.map((c) => c.id + c.nombre).join('|');
  if (clave !== camarasDibujadas) {
    camarasDibujadas = clave;
    selector.replaceChildren(...estado.camaras.map((c) => {
      const opcion = elemento('option', '', c.nombre);
      opcion.value = c.id;
      return opcion;
    }));
  }
  if (document.activeElement !== selector && estado.camara) selector.value = estado.camara;
}

// ---------------------------------------------------------------------
// Interfaz
// ---------------------------------------------------------------------

function elemento(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

function elegirCategoria(id) {
  objetivo = null;
  resultadoPractica = null;
  vista = 'inicio';
  estado.categoria = id;
  estado.palabra = null;
  estado.confianza = 0;
  dibujar();
}

function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  $('texto-tema').textContent = tema === 'oscuro' ? 'Modo oscuro' : 'Modo claro';
  recordar('tema', tema);
}

$('boton-tema').addEventListener('click', () => {
  aplicarTema(document.documentElement.dataset.tema === 'oscuro' ? 'claro' : 'oscuro');
});
aplicarTema(recordado('tema') || 'claro');

document.querySelectorAll('[data-cat]').forEach((boton) => {
  boton.addEventListener('click', () => {
    if (modelos[boton.dataset.cat]) elegirCategoria(boton.dataset.cat);
  });
});
document.querySelector('[data-vista="inicio"]').addEventListener('click', () => elegirCategoria(null));
document.querySelector('[data-vista="ajustes"]').addEventListener('click', () => {
  vista = 'ajustes';
  dibujar();
});

// ---------- Ajustes ----------

$('ajuste-umbral').value = Math.round(estado.ajustes.umbral * 100);
$('ajuste-esqueleto').checked = estado.ajustes.esqueleto;
$('ajuste-espejo').checked = estado.ajustes.espejo;
$('ajuste-umbral').addEventListener('input', (e) => {
  estado.ajustes.umbral = e.target.value / 100;
  dibujar();
});
$('ajuste-esqueleto').addEventListener('change', (e) => { estado.ajustes.esqueleto = e.target.checked; });
$('ajuste-espejo').addEventListener('change', (e) => {
  estado.ajustes.espejo = e.target.checked;
  dibujar();
});

// ---------- Historial ----------

$('historial-ver').addEventListener('click', () => {
  historialCompleto = !historialCompleto;
  dibujar();
});
$('historial-limpiar').addEventListener('click', () => {
  estado.historial = [];
  dibujar();
});

function hace(hora) {
  const segundos = Math.max(0, Math.round((Date.now() - hora) / 1000));
  if (segundos < 2) return 'Ahora';
  if (segundos < 60) return `Hace ${segundos}s`;
  return `Hace ${Math.round(segundos / 60)} min`;
}

function dibujarHistorial() {
  const todos = estado.historial.slice().reverse();
  const visibles = historialCompleto ? todos : todos.slice(0, HISTORIAL_CORTO);
  $('historial').replaceChildren(...visibles.map((item) => {
    const fila = elemento('div', 'history-item');
    const icono = elemento('div', 'hist-icon');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    const trazo = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    trazo.setAttribute('d', ICONO_MANO);
    svg.append(trazo);
    icono.append(svg);

    const info = elemento('div', 'hist-info');
    info.append(elemento('div', 'hist-word', item.palabra), elemento('div', 'hist-type', item.tipo));
    const meta = elemento('div', 'hist-meta');
    meta.append(elemento('div', 'hist-conf', Math.round(item.confianza * 100) + '%'),
                elemento('div', 'hist-time', hace(item.hora)));
    fila.append(icono, info, meta);
    return fila;
  }));

  $('historial-vacio').hidden = todos.length > 0;
  $('historial-limpiar').hidden = todos.length === 0;
  $('historial-ver').hidden = todos.length <= HISTORIAL_CORTO;
  $('historial-ver').textContent = historialCompleto ? 'Ver menos ‹' : 'Ver historial completo ›';
}

// ---------- Señas de la categoria (practica) ----------

function dibujarSenas() {
  const modelo = modelos[estado.categoria];
  $('panel-senas').hidden = !modelo;
  // solo se rearma si cambio algo: reemplazar los botones todo el tiempo
  // haria que se pierdan clics
  const clave = modelo ? modelo.id + '|' + objetivo : '';
  if (clave === senasDibujadas) return;
  senasDibujadas = clave;
  if (!modelo) return;
  $('titulo-senas').textContent = `Señas de ${modelo.titulo} — tocá una para practicarla`;
  $('lista-senas').replaceChildren(...modelo.nombres.filter((n) => n !== null).map((sena) => {
    const boton = elemento('button', 'sena' + (sena === objetivo ? ' active' : ''), sena);
    boton.addEventListener('click', () => {
      objetivo = objetivo === sena ? null : sena;
      resultadoPractica = null;
      dibujar();
    });
    return boton;
  }));
}

function dibujarPractica() {
  const el = $('practica');
  el.hidden = !objetivo;
  if (!objetivo) return;
  el.className = 'practica';
  if (!resultadoPractica) {
    el.textContent = `Hacé la seña de «${objetivo}»`;
  } else if (resultadoPractica.bien) {
    el.textContent = `✓ ¡Correcto! Esa es «${objetivo}»`;
    el.classList.add('bien');
  } else {
    el.textContent = `✗ Eso se reconoció como «${resultadoPractica.palabra}». Probá de nuevo «${objetivo}»`;
    el.classList.add('mal');
  }
}

// ---------- Dibujo general ----------

function situacion() {
  if (estado.fase === 'cargando') return 'Cargando…';
  if (estado.fase === 'sin_camara') return 'Sin cámara';
  if (!estado.categoria) return 'Elegí una categoría para empezar';
  if (!estado.cuerpo) return 'Ponete de frente a la cámara';
  if (!estado.mano && !estado.palabra) return 'Mostrá tu mano y hacé la seña';
  return 'Detectando...';
}

function dibujar() {
  const modelo = modelos[estado.categoria];
  const listo = estado.fase === 'listo';
  const cargando = estado.fase === 'cargando';

  $('punto-sistema').className = 'status-dot' + (listo ? ' activo' : cargando ? '' : ' error');
  $('texto-sistema').textContent = listo ? 'Sistema activo' : cargando ? 'Iniciando…' : 'Sin cámara';
  $('aviso-camara').hidden = listo;
  $('aviso-texto').textContent = estado.mensaje || '';
  $('camara-imagen').classList.toggle('espejo', estado.ajustes.espejo);

  document.querySelectorAll('[data-cat]').forEach((boton) => {
    const disponible = !!modelos[boton.dataset.cat];
    boton.classList.toggle('disabled', !disponible && !cargando);
    boton.classList.toggle('active', vista === 'inicio' && estado.categoria === boton.dataset.cat);
    boton.title = disponible || cargando ? '' : 'Próximamente: esta categoría todavía no tiene señas';
  });
  document.querySelector('[data-vista="inicio"]').classList.toggle('active', vista === 'inicio' && !estado.categoria);
  document.querySelector('[data-vista="ajustes"]').classList.toggle('active', vista === 'ajustes');
  $('panel-categorias').hidden = vista !== 'inicio';
  $('panel-ajustes').hidden = vista !== 'ajustes';
  $('titulo-vista').textContent = modelo ? `Reconocimiento en tiempo real · ${modelo.titulo}` : 'Reconocimiento en tiempo real';
  $('valor-umbral').textContent = Math.round(estado.ajustes.umbral * 100) + '%';

  const porcentaje = Math.round((estado.confianza || 0) * 100);
  $('palabra').textContent = estado.palabra || '—';
  $('palabra').classList.toggle('vacia', !estado.palabra);
  $('tipo').textContent = estado.palabra && modelo ? modelo.tipoSena : ' ';
  $('confianza-texto').textContent = porcentaje + '%';
  $('confianza-barra').style.width = porcentaje + '%';
  $('situacion').textContent = situacion();

  dibujarCamaras();
  dibujarSenas();
  dibujarPractica();
  dibujarHistorial();
}

// ---------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------

async function iniciar() {
  dibujar();
  try {
    await Promise.all([cargarModelos(), crearDetectores()]);
  } catch (e) {
    console.error(e);
    return sinCamara('No se pudo cargar el reconocimiento. Revisá la conexión y recargá la página.', false);
  }
  setInterval(dibujar, 200);   // la pantalla se refresca 5 veces por segundo, no en cada imagen
  if (VIDEO_DE_PRUEBA) return recorrerVideoDePrueba();
  estado.mensaje = 'Abriendo la cámara…';
  dibujar();
  await abrirCamara(recordado('camara'));
  bucle();
}

iniciar();
