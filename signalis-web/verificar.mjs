// Comprueba que el motor en JavaScript da lo mismo que la version en
// Python. Los casos (pruebas/casos.json) los calcula
// app-python/exportar_web.py: los puntos de entrada y lo que Python
// obtuvo con ellos. Aca se hace la misma cuenta con motor.js y se compara.
//
// Uso:  node verificar.mjs

import { readFileSync } from 'node:fs';
import { Modelo, SeguidorDeSena, SeguidorEstatico, featuresDeSecuencia, posturas, resamplear } from './motor.js';

const UMBRAL = 0.6;
const FPS = 30;
const TOLERANCIA_FEATURES = 1e-3;
const TOLERANCIA_PROBS = 5e-3;

const aqui = new URL('.', import.meta.url);
const leer = (ruta) => JSON.parse(readFileSync(new URL(ruta, aqui), 'utf-8'));

function mayorDiferencia(a, b) {
  let peor = 0;
  for (let i = 0; i < a.length; i++) peor = Math.max(peor, Math.abs(a[i] - b[i]));
  return peor;
}

const iguales = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

const casos = leer('pruebas/casos.json');
const modelos = {};
let fallas = 0;

for (const caso of casos) {
  modelos[caso.categoria] ??= new Modelo(leer(`modelos/${caso.categoria}.json`));
  const modelo = modelos[caso.categoria];
  const nombre = (idx) => modelo.nombres[idx] ?? '(nada)';
  let difFeatures = 0;
  let difProbs = 0;
  const detectadas = [];

  if (caso.tipo === 'dinamica') {
    const feats = featuresDeSecuencia(caso.frames.slice(0, caso.cuantos_del_clip), caso.aspecto);
    feats.forEach((f, i) => { difFeatures = Math.max(difFeatures, mayorDiferencia(f, caso.features[i])); });
    difProbs = mayorDiferencia(modelo.predecir(resamplear(feats)), caso.probs);

    const seguidor = new SeguidorDeSena(modelo, caso.aspecto);
    caso.frames.forEach((frame, i) => {
      seguidor.procesar(i / FPS, frame, UMBRAL);
      if (seguidor.nueva) detectadas.push(seguidor.detectada.idx);
    });
  } else {
    const { feats, conMano } = posturas(caso.frames, caso.aspecto);
    feats.forEach((f, i) => {
      difFeatures = Math.max(difFeatures, mayorDiferencia(f, caso.features[i]));
      if (conMano[i] !== caso.con_mano[i]) difFeatures = Infinity;
      if (conMano[i]) difProbs = Math.max(difProbs, mayorDiferencia(modelo.predecir(f), caso.probs[i]));
    });

    const seguidor = new SeguidorEstatico(modelo, caso.aspecto);
    caso.frames.forEach((frame, i) => {
      seguidor.procesar(caso.tiempos[i], frame, UMBRAL);
      if (seguidor.nueva) detectadas.push(seguidor.detectada.idx);
    });
  }

  const bien = difFeatures < TOLERANCIA_FEATURES && difProbs < TOLERANCIA_PROBS && iguales(detectadas, caso.detectadas);
  if (!bien) fallas += 1;
  console.log(`${bien ? 'OK   ' : 'FALLA'} ${caso.categoria.padEnd(10)} ${caso.origen.padEnd(16)} `
    + `features ±${difFeatures.toExponential(1)}  probs ±${difProbs.toExponential(1)}  `
    + `en vivo: ${detectadas.map(nombre).join(' ') || '(nada)'}`
    + (iguales(detectadas, caso.detectadas) ? '' : `   <- Python: ${caso.detectadas.map(nombre).join(' ') || '(nada)'}`));
}

console.log(fallas ? `\n${fallas} de ${casos.length} casos no coinciden con Python.` : `\nLos ${casos.length} casos coinciden con Python.`);
process.exit(fallas ? 1 : 0);
