// ============================================================
// CONFIG — editar esto con la lista final del equipo antes de grabar
// ============================================================
const CONFIG = {
  repeticionesPorPalabra: 10,
  duracionClipMs: 3000, // segundos que graba cada repetición (3000 = 3 seg)
  palabras: [
    "hola",
    "gracias",
    "por favor",
    "familia",
    "amigo",
    "casa",
    "comer",
    "agua",
    "ayuda",
    "perdón",
    "sí",
    "no",
    // ⬆ reemplazar por la lista final elegida en la carpeta de investigación
  ],
};

// ============================================================
// Estado
// ============================================================
const state = {
  pantalla: "setup", // setup | permiso | listo | grabando | revisando | fin
  nombre: "",
  palabraIdx: 0,
  rep: 1,
  clipsGuardados: 0,
  stream: null,
  mediaRecorder: null,
  chunks: [],
  ultimoBlob: null,
  ultimaUrl: null,
  mimeType: "video/webm",
};

const app = document.getElementById("app");

function totalClips() {
  return CONFIG.palabras.length * CONFIG.repeticionesPorPalabra;
}

function palabraActual() {
  return CONFIG.palabras[state.palabraIdx];
}

function slug(s) {
  return s
    .toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "") // saca tildes
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function pad(n, len) {
  return String(n).padStart(len, "0");
}

// ============================================================
// Render
// ============================================================
function render() {
  app.innerHTML = "";
  const view = {
    setup: renderSetup,
    permiso: renderPermiso,
    listo: renderListo,
    grabando: renderGrabando,
    revisando: renderRevisando,
    fin: renderFin,
  }[state.pantalla];
  view();
}

function el(tag, className, html) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function renderSetup() {
  const card = el("div", "card");
  card.appendChild(el("h1", null, "Captura de señas — LSA"));
  card.appendChild(
    el("p", "lede", `${CONFIG.palabras.length} palabras × ${CONFIG.repeticionesPorPalabra} repeticiones = ${totalClips()} clips en esta sesión.`)
  );

  const label = el("label", null, "Tu nombre (va en el archivo de cada clip)");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Ej: Mateo";
  input.value = state.nombre;
  input.autocomplete = "off";

  const btn = el("button", "btn-primary", "Empezar");
  btn.disabled = !state.nombre.trim();
  input.addEventListener("input", () => {
    state.nombre = input.value;
    btn.disabled = !state.nombre.trim();
  });
  btn.addEventListener("click", () => {
    state.pantalla = "permiso";
    render();
    pedirCamara();
  });

  card.appendChild(label);
  card.appendChild(input);
  card.appendChild(btn);
  card.appendChild(el("p", "hint", "Se piden permisos de cámara al tocar Empezar. No se sube nada a ningún servidor: cada clip se descarga a este dispositivo."));
  app.appendChild(card);
}

function renderPermiso() {
  const card = el("div", "card");
  card.appendChild(el("h1", null, "Pidiendo acceso a la cámara…"));
  card.appendChild(el("p", "lede", "Aceptá el permiso cuando lo pida el navegador."));
  app.appendChild(card);
}

async function pedirCamara() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1080 }, height: { ideal: 1440 } },
      audio: false,
    });
    state.stream = stream;
    state.mimeType = pickMimeType();
    state.pantalla = "listo";
    render();
  } catch (err) {
    app.innerHTML = "";
    const card = el("div", "card");
    card.appendChild(el("h1", null, "No se pudo acceder a la cámara"));
    card.appendChild(el("div", "error-box", `${err.message || err}. Revisá los permisos de cámara del navegador y volvé a intentar.`));
    const btn = el("button", "btn-secondary", "Reintentar");
    btn.addEventListener("click", () => { state.pantalla = "setup"; render(); });
    card.appendChild(btn);
    app.appendChild(card);
  }
}

function pickMimeType() {
  const candidatos = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
    "video/mp4",
  ];
  for (const m of candidatos) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
  }
  return "";
}

function crearVideoPreview() {
  const wrap = el("div", "video-wrap");
  const video = document.createElement("video");
  video.autoplay = true;
  video.muted = true;
  video.playsInline = true;
  video.srcObject = state.stream;
  wrap.appendChild(video);
  return wrap;
}

function renderListo() {
  const card = el("div", "card");

  const bar = el("div", "progress-bar");
  const fill = el("div", "progress-fill");
  fill.style.width = `${(state.clipsGuardados / totalClips()) * 100}%`;
  bar.appendChild(fill);
  card.appendChild(bar);

  const wrap = crearVideoPreview();
  const badge = el("div", "badge", `${state.clipsGuardados}/${totalClips()} guardados`);
  wrap.appendChild(badge);
  card.appendChild(wrap);

  const wordBox = el("div", "word-box");
  wordBox.appendChild(el("div", "word-eyebrow", `Repetición ${state.rep} de ${CONFIG.repeticionesPorPalabra}`));
  wordBox.appendChild(el("div", "word-title", palabraActual()));
  card.appendChild(wordBox);

  const btn = el("button", "btn-primary", "● Grabar");
  btn.addEventListener("click", iniciarGrabacion);
  card.appendChild(btn);
  card.appendChild(el("p", "hint", `Tocá Grabar (o <span class="kbd">espacio</span> en notebook) — arranca en 3, graba ${(CONFIG.duracionClipMs / 1000).toFixed(0)}s.`));

  app.appendChild(card);
}

async function iniciarGrabacion() {
  state.pantalla = "grabando";
  render();

  const wrap = document.querySelector(".video-wrap");
  const overlay = el("div", "countdown", "3");
  wrap.appendChild(overlay);

  let n = 3;
  await new Promise((resolve) => {
    const iv = setInterval(() => {
      n -= 1;
      if (n === 0) {
        overlay.remove();
        clearInterval(iv);
        resolve();
      } else {
        overlay.textContent = String(n);
      }
    }, 700);
  });

  grabarClip();
}

function grabarClip() {
  const wrap = document.querySelector(".video-wrap");
  const recDot = el("div", "rec-dot", "REC");
  wrap.appendChild(recDot);

  state.chunks = [];
  const options = state.mimeType ? { mimeType: state.mimeType } : undefined;
  const recorder = new MediaRecorder(state.stream, options);
  state.mediaRecorder = recorder;

  recorder.ondataavailable = (e) => { if (e.data.size > 0) state.chunks.push(e.data); };
  recorder.onstop = () => {
    const blob = new Blob(state.chunks, { type: state.mimeType || "video/webm" });
    state.ultimoBlob = blob;
    state.ultimaUrl = URL.createObjectURL(blob);
    state.pantalla = "revisando";
    render();
  };

  recorder.start();
  setTimeout(() => {
    if (recorder.state !== "inactive") recorder.stop();
  }, CONFIG.duracionClipMs);
}

function renderGrabando() {
  const card = el("div", "card");
  const wrap = crearVideoPreview();
  card.appendChild(wrap);
  const wordBox = el("div", "word-box");
  wordBox.appendChild(el("div", "word-eyebrow", `Repetición ${state.rep} de ${CONFIG.repeticionesPorPalabra}`));
  wordBox.appendChild(el("div", "word-title", palabraActual()));
  card.appendChild(wordBox);
  app.appendChild(card);
}

function renderRevisando() {
  const card = el("div", "card");

  const wrap = el("div", "video-wrap");
  const video = document.createElement("video");
  video.src = state.ultimaUrl;
  video.controls = true;
  video.autoplay = true;
  video.loop = true;
  video.playsInline = true;
  wrap.appendChild(video);
  card.appendChild(wrap);

  const wordBox = el("div", "word-box");
  wordBox.appendChild(el("div", "word-eyebrow", `Repetición ${state.rep} de ${CONFIG.repeticionesPorPalabra}`));
  wordBox.appendChild(el("div", "word-title", palabraActual()));
  card.appendChild(wordBox);

  const row = el("div", "row-btns");
  const btnRepetir = el("button", "btn-danger", "↺ Repetir");
  const btnGuardar = el("button", "btn-primary", "✓ Guardar y siguiente");
  btnRepetir.addEventListener("click", () => {
    URL.revokeObjectURL(state.ultimaUrl);
    state.pantalla = "listo";
    render();
  });
  btnGuardar.addEventListener("click", guardarYSiguiente);
  row.appendChild(btnRepetir);
  row.appendChild(btnGuardar);
  card.appendChild(row);

  card.appendChild(el("p", "hint", `<span class="kbd">espacio</span> guarda y sigue · <span class="kbd">r</span> repite`));

  app.appendChild(card);
}

function guardarYSiguiente() {
  const ext = state.mimeType.includes("mp4") ? "mp4" : "webm";
  const nombreArchivo = `${pad(state.clipsGuardados + 1, 3)}_${slug(palabraActual())}_${slug(state.nombre)}_rep${pad(state.rep, 2)}.${ext}`;

  const a = document.createElement("a");
  a.href = state.ultimaUrl;
  a.download = nombreArchivo;
  document.body.appendChild(a);
  a.click();
  a.remove();

  state.clipsGuardados += 1;

  if (state.rep < CONFIG.repeticionesPorPalabra) {
    state.rep += 1;
  } else {
    state.rep = 1;
    state.palabraIdx += 1;
  }

  if (state.palabraIdx >= CONFIG.palabras.length) {
    if (state.stream) state.stream.getTracks().forEach((t) => t.stop());
    state.pantalla = "fin";
  } else {
    state.pantalla = "listo";
  }
  render();
}

function renderFin() {
  const card = el("div", "card");
  card.appendChild(el("h1", null, "¡Listo! 🎉"));
  const summary = el("div", "summary", `
    <b>${state.nombre}</b> grabó <b>${state.clipsGuardados}</b> clips
    (${CONFIG.palabras.length} palabras × ${CONFIG.repeticionesPorPalabra} repeticiones).<br><br>
    Los archivos quedaron en la carpeta de <b>Descargas</b> de este dispositivo.<br>
    Subilos a la carpeta compartida del equipo para juntarlos con los del resto.
  `);
  card.appendChild(summary);
  const btn = el("button", "btn-secondary", "Grabar de nuevo (otra persona)");
  btn.addEventListener("click", () => {
    state.pantalla = "setup";
    state.nombre = "";
    state.palabraIdx = 0;
    state.rep = 1;
    state.clipsGuardados = 0;
    render();
  });
  card.appendChild(btn);
  app.appendChild(card);
}

// ============================================================
// Atajos de teclado (para notebooks — agiliza mucho la sesión)
// ============================================================
document.addEventListener("keydown", (e) => {
  if (e.code === "Space") {
    e.preventDefault();
    if (state.pantalla === "listo") iniciarGrabacion();
    else if (state.pantalla === "revisando") guardarYSiguiente();
  } else if (e.key.toLowerCase() === "r" && state.pantalla === "revisando") {
    document.querySelector(".btn-danger")?.click();
  }
});

render();
