// Motor de SIGNALIS para el navegador: las mismas cuentas que hace la
// version de escritorio en Python (app-python/landmarks.py, reconocedor.py
// y estaticas.py), escritas en JavaScript y sin ninguna libreria.
//
// No sabe nada de camaras ni de pantallas: recibe los puntos de las manos
// y del cuerpo de cada instante y dice que seña se hizo. Por eso se puede
// comprobar contra Python con `node verificar.mjs`.
//
// Un "frame" es lo que MediaPipe vio en un instante:
//   { manos: [mano "Left", mano "Right"], cada una 21 puntos [x, y, z],
//     presente: [bool, bool], cuerpo: [nariz, hombro, hombro] como [x, y],
//     cuerpo_ok: bool }

export const NADA = '_nada';

const MUNECA = 0;
const PUNTA_INDICE = 8;
const NUDILLO_MEDIO = 9;
const PUNTOS = 21;
const LONGITUD_SECUENCIA = 30;
const MANO_EN_REPOSO = 1.1;   // una muñeca mas abajo que esto (en anchos de hombros) esta en reposo

// --- señas con movimiento ---
const VENTANAS_S = [1.0, 1.5, 2.2];
const MINIMO_S = 0.6;
const SIN_MANO_S = 0.7;
const FRAMES_ENTRE_PREDICCIONES = 4;
const SUAVIZADO = 3;
const RETENER_S = 2.0;

// --- señas quietas ---
const SOSTENER_S = 0.5;
const RETENER_QUIETA_S = 1.0;
const SUAVIZADO_QUIETA = 8;
const REFERENCIA = 15;

// ---------------------------------------------------------------------
// Caracteristicas: de los puntos a los numeros que ve el modelo
// ---------------------------------------------------------------------

function mediana(valores) {
  const v = [...valores].sort((a, b) => a - b);
  const n = v.length;
  return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2;
}

// Donde esta la cara y cuanto miden los hombros, en toda la secuencia.
// Se usa la mediana: la cabeza casi no se mueve durante una seña, y asi
// no molesta que la mano tape la cara en algunos frames.
function referencia(frames, aspecto) {
  const vistos = frames.filter((f) => f.cuerpo_ok);
  if (!vistos.length) return null;
  const ancho = mediana(vistos.map((f) => Math.hypot(
    (f.cuerpo[1][0] - f.cuerpo[2][0]) * aspecto, f.cuerpo[1][1] - f.cuerpo[2][1])));
  return {
    x: mediana(vistos.map((f) => f.cuerpo[0][0] * aspecto)),
    y: mediana(vistos.map((f) => f.cuerpo[0][1])),
    ancho: Math.max(ancho, 1e-3),
  };
}

// La forma de una mano: cada punto medido desde la muñeca y dividido por
// el tamaño de la mano. Devuelve tambien donde esta cada punto respecto
// de la cara, en anchos de hombros.
function manoNormalizada(puntos, ref, aspecto) {
  const m = puntos[MUNECA];
  const n = puntos[NUDILLO_MEDIO];
  const tamano = Math.max(Math.hypot((n[0] - m[0]) * aspecto, n[1] - m[1], (n[2] - m[2]) * aspecto), 1e-4);
  const forma = new Float32Array(PUNTOS * 3);
  const lugar = [];
  for (let i = 0; i < PUNTOS; i++) {
    const p = puntos[i];
    forma[i * 3] = (p[0] - m[0]) * aspecto / tamano;
    forma[i * 3 + 1] = (p[1] - m[1]) / tamano;
    forma[i * 3 + 2] = (p[2] - m[2]) * aspecto / tamano;
    lugar.push([(p[0] * aspecto - ref.x) / ref.ancho, (p[1] - ref.y) / ref.ancho]);
  }
  return { forma, lugar };
}

// Señas con movimiento: por cada frame, 132 numeros (66 por mano: su
// forma, donde esta la muñeca respecto de la cara y un 1 si esta presente).
// Devuelve null si en ningun frame se vio el cuerpo.
export function featuresDeSecuencia(frames, aspecto) {
  const ref = referencia(frames, aspecto);
  if (!ref) return null;
  return frames.map((f) => {
    const salida = new Float32Array(132);
    for (let h = 0; h < 2; h++) {
      if (!f.presente[h]) continue;
      const { forma, lugar } = manoNormalizada(f.manos[h], ref, aspecto);
      salida.set(forma, h * 66);
      salida[h * 66 + 63] = lugar[MUNECA][0];
      salida[h * 66 + 64] = lugar[MUNECA][1];
      salida[h * 66 + 65] = 1;
    }
    return salida;
  });
}

// Señas quietas: por cada frame, 135 numeros. La mano principal (la que
// esta mas arriba): su forma y donde estan la muñeca, la punta del indice
// y el centro de la palma. La otra mano, si esta levantada: su forma y
// donde esta respecto de la principal. Si la principal es la izquierda se
// espeja todo, para que la seña valga con cualquiera de las dos manos.
export function posturas(frames, aspecto) {
  const ref = referencia(frames, aspecto);
  if (!ref) return null;
  const feats = [];
  const conMano = [];
  for (const f of frames) {
    const manos = [0, 1].map((h) => manoNormalizada(f.manos[h], ref, aspecto));
    const levantada = [0, 1].map((h) => f.presente[h] && manos[h].lugar[MUNECA][1] < MANO_EN_REPOSO);
    const hayMano = levantada[0] || levantada[1];
    const salida = new Float32Array(135);
    conMano.push(hayMano);
    feats.push(salida);
    if (!hayMano) continue;

    const altura = (h) => (levantada[h] ? manos[h].lugar[MUNECA][1] : Infinity);
    const principal = altura(1) < altura(0) ? 1 : 0;
    const otra = 1 - principal;
    const espejo = principal === 0 ? -1 : 1;
    const p = manos[principal];
    const o = manos[otra];

    for (let i = 0; i < 63; i++) salida[i] = p.forma[i] * (i % 3 === 0 ? espejo : 1);
    [MUNECA, PUNTA_INDICE, NUDILLO_MEDIO].forEach((punto, k) => {
      salida[63 + k * 2] = p.lugar[punto][0] * espejo;
      salida[64 + k * 2] = p.lugar[punto][1];
    });
    if (levantada[otra]) {
      for (let i = 0; i < 63; i++) salida[69 + i] = o.forma[i] * (i % 3 === 0 ? espejo : 1);
      salida[132] = (o.lugar[MUNECA][0] - p.lugar[MUNECA][0]) * espejo;
      salida[133] = o.lugar[MUNECA][1] - p.lugar[MUNECA][1];
      salida[134] = 1;
    }
  }
  return { feats, conMano };
}

// Redondeo "al par" (0.5 -> 0, 1.5 -> 2), como hace numpy.
function redondear(x) {
  const piso = Math.floor(x);
  const resto = x - piso;
  if (resto < 0.5) return piso;
  if (resto > 0.5) return piso + 1;
  return piso % 2 === 0 ? piso : piso + 1;
}

// Estira o comprime una secuencia a exactamente LONGITUD_SECUENCIA frames.
export function resamplear(secuencia) {
  const total = secuencia.length;
  const salida = [];
  for (let i = 0; i < LONGITUD_SECUENCIA; i++) {
    salida.push(secuencia[redondear(i * (total - 1) / (LONGITUD_SECUENCIA - 1))]);
  }
  return salida;
}

// ---------------------------------------------------------------------
// La red neuronal: las cuentas de cada capa, con los pesos que exporta
// app-python/exportar_web.py
// ---------------------------------------------------------------------

function tensor(t) {
  const binario = atob(t.datos);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

const sigmoide = (x) => 1 / (1 + Math.exp(-x));

function densa(capa, x) {
  const salen = capa.sesgo.length;
  const y = new Float32Array(salen);
  for (let j = 0; j < salen; j++) {
    let suma = capa.sesgo[j];
    for (let i = 0; i < x.length; i++) suma += x[i] * capa.pesos[i * salen + j];
    y[j] = suma;
  }
  if (capa.activacion === 'relu') {
    for (let j = 0; j < salen; j++) y[j] = Math.max(0, y[j]);
  } else if (capa.activacion === 'softmax') {
    const maximo = Math.max(...y);
    let total = 0;
    for (let j = 0; j < salen; j++) { y[j] = Math.exp(y[j] - maximo); total += y[j]; }
    for (let j = 0; j < salen; j++) y[j] /= total;
  }
  return y;
}

// Una LSTM recorriendo la secuencia en un sentido. Devuelve lo que
// recuerda en cada paso, puesto en el lugar del frame que acaba de leer.
function lstm(pesos, unidades, secuencia, alReves) {
  const u = unidades;
  const h = new Float32Array(u);
  const c = new Float32Array(u);
  const z = new Float32Array(4 * u);
  const salidas = new Array(secuencia.length);
  for (let paso = 0; paso < secuencia.length; paso++) {
    const t = alReves ? secuencia.length - 1 - paso : paso;
    const x = secuencia[t];
    z.set(pesos.sesgo);
    for (let i = 0; i < x.length; i++) {
      const xi = x[i];
      if (xi === 0) continue;
      const fila = i * 4 * u;
      for (let j = 0; j < 4 * u; j++) z[j] += xi * pesos.nucleo[fila + j];
    }
    for (let i = 0; i < u; i++) {
      const hi = h[i];
      const fila = i * 4 * u;
      for (let j = 0; j < 4 * u; j++) z[j] += hi * pesos.recurrente[fila + j];
    }
    // las cuatro compuertas, en el orden de Keras: entrada, olvido, candidato, salida
    for (let j = 0; j < u; j++) {
      c[j] = sigmoide(z[u + j]) * c[j] + sigmoide(z[j]) * Math.tanh(z[2 * u + j]);
      h[j] = sigmoide(z[3 * u + j]) * Math.tanh(c[j]);
    }
    salidas[t] = Float32Array.from(h);
  }
  return salidas;
}

function unir(a, b) {
  const y = new Float32Array(a.length + b.length);
  y.set(a);
  y.set(b, a.length);
  return y;
}

// LSTM bidireccional: lee la secuencia hacia adelante y hacia atras y junta las dos lecturas.
function bilstm(capa, secuencia) {
  const adelante = lstm(capa.adelante, capa.unidades, secuencia, false);
  const atras = lstm(capa.atras, capa.unidades, secuencia, true);
  if (capa.secuencia) return secuencia.map((_, t) => unir(adelante[t], atras[t]));
  return unir(adelante[secuencia.length - 1], atras[0]);
}

export class Modelo {
  // `datos` es el contenido de modelos/<categoria>.json
  constructor(datos) {
    this.id = datos.id;
    this.titulo = datos.titulo;
    this.tipoSena = datos.tipo_sena;
    this.estatica = datos.estatica;
    this.clases = datos.clases;
    this.nombres = datos.nombres;
    this.nada = datos.clases.indexOf(NADA);
    this.capas = datos.capas.map((capa) => (capa.tipo === 'bilstm'
      ? { ...capa,
          adelante: { nucleo: tensor(capa.adelante.nucleo), recurrente: tensor(capa.adelante.recurrente), sesgo: tensor(capa.adelante.sesgo) },
          atras: { nucleo: tensor(capa.atras.nucleo), recurrente: tensor(capa.atras.recurrente), sesgo: tensor(capa.atras.sesgo) } }
      : { ...capa, pesos: tensor(capa.pesos), sesgo: tensor(capa.sesgo) }));
  }

  // Una secuencia de 30 frames (señas con movimiento) o una postura
  // (señas quietas) -> la probabilidad de cada clase.
  predecir(entrada) {
    let x = entrada;
    for (const capa of this.capas) x = capa.tipo === 'bilstm' ? bilstm(capa, x) : densa(capa, x);
    return x;
  }
}

function indiceDelMayor(valores) {
  let mejor = 0;
  for (let i = 1; i < valores.length; i++) if (valores[i] > valores[mejor]) mejor = i;
  return mejor;
}

function promedio(vectores) {
  const y = new Float32Array(vectores[0].length);
  for (const v of vectores) for (let i = 0; i < y.length; i++) y[i] += v[i] / vectores.length;
  return y;
}

// ---------------------------------------------------------------------
// Seguidores: reciben un frame por vez y deciden que seña se esta haciendo.
// Despues de cada procesar():
//   detectada = { idx, confianza, t } de la seña vigente, o null
//   nueva     = true solo en el frame en que aparece una seña
//   confianza = la de la prediccion actual
// ---------------------------------------------------------------------

export class SeguidorDeSena {
  constructor(modelo, aspecto) {
    this.modelo = modelo;
    this.aspecto = aspecto;
    this.buffer = [];
    this.recientes = [];
    this.ultimaManoT = null;
    this.frames = 0;
    this.confianza = 0;
    this.detectada = null;
    this.candidata = null;   // seña vista en la prediccion anterior
    this.nueva = false;
  }

  procesar(t, frame, umbral) {
    this.nueva = false;
    this.frames += 1;

    if (frame.presente[0] || frame.presente[1]) {
      this.ultimaManoT = t;
    } else if (this.ultimaManoT === null || t - this.ultimaManoT > SIN_MANO_S) {
      // sin manos: se termina la seña y se empieza de cero
      this.buffer = [];
      this.recientes = [];
      this.candidata = null;
      this.confianza = 0;
      this.ultimaManoT = null;
      this.vencer(t);
      return;
    }

    this.buffer.push({ t, frame });
    while (t - this.buffer[0].t > VENTANAS_S[VENTANAS_S.length - 1]) this.buffer.shift();

    if (this.frames % FRAMES_ENTRE_PREDICCIONES === 0 && t - this.buffer[0].t >= MINIMO_S) {
      this.predecir(t, umbral);
    }
    this.vencer(t);
  }

  vencer(t) {
    if (this.detectada && t - this.detectada.t > RETENER_S) this.detectada = null;
  }

  predecir(t, umbral) {
    // Nadie hace una seña siempre a la misma velocidad: se prueba con
    // varias ventanas hacia atras y se usa la que el modelo ve mas clara.
    let mejor = null;
    let mejorValor = -1;
    for (const ventana of VENTANAS_S) {
      const desde = this.buffer.findIndex((b) => b.t >= t - ventana);
      const feats = featuresDeSecuencia(this.buffer.slice(desde).map((b) => b.frame), this.aspecto);
      if (!feats) return;
      const probs = this.modelo.predecir(resamplear(feats));
      let valor = -1;
      for (let i = 0; i < probs.length; i++) if (i !== this.modelo.nada && probs[i] > valor) valor = probs[i];
      if (valor > mejorValor) { mejorValor = valor; mejor = probs; }
      if (desde === 0) break;   // las ventanas mas largas serian esta misma
    }

    this.recientes.push(mejor);
    if (this.recientes.length > SUAVIZADO) this.recientes.shift();
    const media = promedio(this.recientes);
    const idx = indiceDelMayor(media);
    const esNada = idx === this.modelo.nada;
    this.confianza = esNada ? 0 : media[idx];
    const acepta = !esNada && this.confianza >= umbral;
    // Una seña nueva tiene que sostenerse dos predicciones seguidas:
    // filtra los falsos de un instante, tipicos de cuando la mano baja.
    const sigue = this.detectada !== null && this.detectada.idx === idx;
    if (acepta && (idx === this.candidata || sigue)) {
      this.nueva = !sigue;
      this.detectada = { idx, confianza: this.confianza, t };
    }
    this.candidata = acepta ? idx : null;
  }
}

export class SeguidorEstatico {
  constructor(modelo, aspecto) {
    this.modelo = modelo;
    this.aspecto = aspecto;
    this.frames = [];
    this.recientes = [];
    this.candidata = null;   // { idx, desde }: seña que se viene sosteniendo
    this.confianza = 0;
    this.detectada = null;
    this.nueva = false;
  }

  procesar(t, frame, umbral) {
    this.nueva = false;
    this.frames.push(frame);
    if (this.frames.length > REFERENCIA) this.frames.shift();

    const r = posturas(this.frames, this.aspecto);
    if (!r || !r.conMano[r.conMano.length - 1]) {
      this.recientes = [];
      this.candidata = null;
      this.confianza = 0;
    } else {
      this.recientes.push(this.modelo.predecir(r.feats[r.feats.length - 1]));
      if (this.recientes.length > SUAVIZADO_QUIETA) this.recientes.shift();
      const media = promedio(this.recientes);
      const idx = indiceDelMayor(media);
      this.confianza = media[idx];
      if (this.confianza < umbral) {
        this.candidata = null;
      } else {
        if (this.candidata === null || this.candidata.idx !== idx) this.candidata = { idx, desde: t };
        const sigue = this.detectada !== null && this.detectada.idx === idx;
        if (sigue || t - this.candidata.desde >= SOSTENER_S) {
          this.nueva = !sigue;
          this.detectada = { idx, confianza: this.confianza, t };
        }
      }
    }
    if (this.detectada && t - this.detectada.t > RETENER_QUIETA_S) this.detectada = null;
  }
}

export function crearSeguidor(modelo, aspecto) {
  return modelo.estatica ? new SeguidorEstatico(modelo, aspecto) : new SeguidorDeSena(modelo, aspecto);
}
