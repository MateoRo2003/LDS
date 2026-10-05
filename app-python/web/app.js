// Interfaz de SIGNALIS. Toda la inteligencia esta en Python (reconocedor.py):
// esta pagina solo muestra el video de /video, le pregunta a /api/estado
// varias veces por segundo que esta viendo, y le avisa que categoria se eligio.

const $ = (id) => document.getElementById(id);
const ICONO_MANO = 'M12.5 2C11.1 2 10 3.1 10 4.5V11H8.5C7.1 11 6 12.1 6 13.5V19C6 20.7 7.3 22 9 22H15C16.7 22 18 20.7 18 19V4.5C18 3.1 16.9 2 15.5 2H12.5Z';
const HISTORIAL_CORTO = 3;

let vista = 'inicio';          // 'inicio' o 'ajustes'
let estado = null;             // ultima respuesta de /api/estado
let objetivo = null;           // seña que se esta practicando
let resultadoPractica = null;  // { bien, palabra } de la ultima seña hecha
let ultimoIdVisto = 0;
let historialCompleto = false;
let ajustesCargados = false;
let senasDibujadas = null;

function enviar(ruta, datos) {
  return fetch(ruta, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datos || {}),
  });
}

function categoriaActual() {
  return estado && estado.categorias.find((c) => c.id === estado.categoria);
}

function elegirCategoria(id) {
  objetivo = null;
  resultadoPractica = null;
  vista = 'inicio';
  if (estado) estado.categoria = id;
  enviar('/api/categoria', { id });
  dibujar();
}

// ---------- Tema claro / oscuro ----------

function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  $('texto-tema').textContent = tema === 'oscuro' ? 'Modo oscuro' : 'Modo claro';
  try { localStorage.setItem('tema', tema); } catch (e) { /* sin almacenamiento: no pasa nada */ }
}

$('boton-tema').addEventListener('click', () => {
  aplicarTema(document.documentElement.dataset.tema === 'oscuro' ? 'claro' : 'oscuro');
});

try { aplicarTema(localStorage.getItem('tema') || 'claro'); } catch (e) { aplicarTema('claro'); }

// ---------- Navegacion ----------

document.querySelectorAll('[data-cat]').forEach((boton) => {
  boton.addEventListener('click', () => {
    const cat = estado && estado.categorias.find((c) => c.id === boton.dataset.cat);
    if (cat && cat.disponible) elegirCategoria(cat.id);
  });
});

document.querySelector('[data-vista="inicio"]').addEventListener('click', () => elegirCategoria(null));
document.querySelector('[data-vista="ajustes"]').addEventListener('click', () => {
  vista = 'ajustes';
  dibujar();
});

// ---------- Camara ----------

const BUSCAR_CAMARAS = 'buscar';
let camarasDibujadas = '';

$('selector-camara').addEventListener('change', (e) => {
  if (e.target.value === BUSCAR_CAMARAS) {
    enviar('/api/camara', { buscar: true });
    e.target.value = estado.camara;
  } else {
    estado.camara = Number(e.target.value);
    enviar('/api/camara', { id: estado.camara });
  }
});

function dibujarCamaras() {
  const selector = $('selector-camara');
  const clave = estado.camaras.join(',');
  if (clave !== camarasDibujadas) {
    camarasDibujadas = clave;
    const opciones = estado.camaras.map((id) => {
      const opcion = elemento('option', '', `Cámara ${id + 1}`);
      opcion.value = id;
      return opcion;
    });
    const buscar = elemento('option', '', 'Buscar cámaras de nuevo…');
    buscar.value = BUSCAR_CAMARAS;
    selector.replaceChildren(...opciones, buscar);
  }
  if (document.activeElement !== selector) selector.value = estado.camara;
}

// ---------- Ajustes ----------

$('ajuste-umbral').addEventListener('input', (e) => {
  $('valor-umbral').textContent = e.target.value + '%';
  enviar('/api/ajustes', { umbral: e.target.value / 100 });
});
$('ajuste-esqueleto').addEventListener('change', (e) => enviar('/api/ajustes', { esqueleto: e.target.checked }));
$('ajuste-espejo').addEventListener('change', (e) => enviar('/api/ajustes', { espejo: e.target.checked }));

// ---------- Historial ----------

$('historial-ver').addEventListener('click', () => {
  historialCompleto = !historialCompleto;
  dibujar();
});
$('historial-limpiar').addEventListener('click', () => {
  enviar('/api/historial/limpiar');
  if (estado) estado.historial = [];
  dibujar();
});

function hace(hora) {
  const segundos = Math.max(0, Math.round(Date.now() / 1000 - hora));
  if (segundos < 2) return 'Ahora';
  if (segundos < 60) return `Hace ${segundos}s`;
  return `Hace ${Math.round(segundos / 60)} min`;
}

function elemento(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

function dibujarHistorial() {
  const todos = estado.historial.slice().reverse();
  const visibles = historialCompleto ? todos : todos.slice(0, HISTORIAL_CORTO);
  const lista = $('historial');
  lista.replaceChildren(...visibles.map((item) => {
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
  const cat = categoriaActual();
  $('panel-senas').hidden = !cat;
  // solo se rearma si cambio algo: reemplazar los botones todo el tiempo
  // haria que se pierdan clics
  const clave = cat ? cat.id + '|' + objetivo : '';
  if (clave === senasDibujadas) return;
  senasDibujadas = clave;
  if (!cat) return;
  $('titulo-senas').textContent = `Señas de ${cat.titulo} — tocá una para practicarla`;
  $('lista-senas').replaceChildren(...cat.senas.map((sena) => {
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
  if (estado.fase === 'error') return 'Error';
  if (!estado.categoria) return 'Elegí una categoría para empezar';
  if (!estado.cuerpo) return 'Ponete de frente a la cámara';
  if (!estado.mano && !estado.palabra) return 'Mostrá tu mano y hacé la seña';
  return 'Detectando...';
}

function dibujar() {
  if (!estado) return;
  const cat = categoriaActual();
  const listo = estado.fase === 'listo';

  const cargando = estado.fase === 'cargando';
  $('punto-sistema').className = 'status-dot' + (listo ? ' activo' : cargando ? '' : ' error');
  $('texto-sistema').textContent = listo ? 'Sistema activo' : cargando ? 'Iniciando…' : situacion();
  $('aviso-camara').hidden = listo;
  $('aviso-camara').textContent = estado.mensaje || '';

  document.querySelectorAll('[data-cat]').forEach((boton) => {
    const info = estado.categorias.find((c) => c.id === boton.dataset.cat);
    const disponible = info && info.disponible;
    boton.classList.toggle('disabled', !disponible);
    boton.classList.toggle('active', vista === 'inicio' && estado.categoria === boton.dataset.cat);
    boton.title = disponible ? '' : 'Próximamente: esta categoría todavía no tiene señas';
    if (boton.classList.contains('cat-card')) {
      const pronto = boton.querySelector('.pronto');
      if (disponible && pronto) pronto.remove();
      if (!disponible && !pronto) boton.append(elemento('span', 'pronto', 'Próximamente'));
    }
  });
  document.querySelector('[data-vista="inicio"]').classList.toggle('active', vista === 'inicio' && !estado.categoria);
  document.querySelector('[data-vista="ajustes"]').classList.toggle('active', vista === 'ajustes');
  $('panel-categorias').hidden = vista !== 'inicio';
  $('panel-ajustes').hidden = vista !== 'ajustes';
  $('titulo-vista').textContent = cat ? `Reconocimiento en tiempo real · ${cat.titulo}` : 'Reconocimiento en tiempo real';

  if (!ajustesCargados) {
    $('ajuste-umbral').value = Math.round(estado.ajustes.umbral * 100);
    $('valor-umbral').textContent = $('ajuste-umbral').value + '%';
    $('ajuste-esqueleto').checked = estado.ajustes.esqueleto;
    $('ajuste-espejo').checked = estado.ajustes.espejo;
    ajustesCargados = true;
  }

  const porcentaje = Math.round((estado.confianza || 0) * 100);
  $('palabra').textContent = estado.palabra || '—';
  $('palabra').classList.toggle('vacia', !estado.palabra);
  $('tipo').textContent = estado.palabra && cat ? cat.tipo : ' ';
  $('confianza-texto').textContent = porcentaje + '%';
  $('confianza-barra').style.width = porcentaje + '%';
  $('situacion').textContent = situacion();

  dibujarCamaras();
  dibujarSenas();
  dibujarPractica();
  dibujarHistorial();
}

async function actualizar() {
  try {
    const respuesta = await fetch('/api/estado');
    estado = await respuesta.json();

    // cada entrada nueva del historial es una seña recien hecha
    const ultima = estado.historial[estado.historial.length - 1];
    if (ultima && ultima.id !== ultimoIdVisto) {
      if (ultimoIdVisto !== 0 && objetivo) {
        resultadoPractica = { bien: ultima.palabra === objetivo, palabra: ultima.palabra };
      }
      ultimoIdVisto = ultima.id;
    } else if (!ultima) {
      ultimoIdVisto = -1;
    }
    dibujar();
  } catch (e) {
    $('punto-sistema').className = 'status-dot error';
    $('texto-sistema').textContent = 'Aplicación cerrada';
    $('situacion').textContent = 'Volvé a abrir la aplicación';
  }
  setTimeout(actualizar, 200);
}

actualizar();
