"""
Lanzador unico de la app — esto es lo que se corre en la expo, no los
scripts sueltos.

Abre la interfaz (web/) en una ventana y arranca el reconocimiento. La
interfaz es una pagina que sirve este mismo programa en la propia
maquina: no hace falta internet ni instalar nada mas. Las categorias se
eligen y se cambian desde la interfaz, con la camara siempre abierta.

Para cerrar: cerrar la ventana (o Ctrl+C en la consola).

Uso:
    python app.py
"""
import json
import os
import shutil
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from reconocedor import Reconocedor, info_categorias

CARPETA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
ARCHIVOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
PUERTO = 8765
# Si la ventana se cierra, la app se apaga sola a los pocos segundos.
ESPERA_SIN_VENTANA_S = 6

reconocedor = Reconocedor()
ventanas = {"abiertas": 0, "ultima_vez": None}


class Pedido(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # sin una linea en consola por cada pedido

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path in ARCHIVOS:
            nombre, tipo = ARCHIVOS[self.path]
            with open(os.path.join(CARPETA_WEB, nombre), "rb") as f:
                cuerpo = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)
        elif self.path == "/api/estado":
            self._json({**reconocedor.estado(), "categorias": info_categorias()})
        elif self.path == "/video":
            self._video()
        else:
            self.send_error(404)

    def _video(self):
        """La camara como MJPEG: una seguidilla de JPEGs que un <img> muestra solo."""
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        ventanas["abiertas"] += 1
        try:
            while True:
                with reconocedor.hay_frame:
                    if not reconocedor.hay_frame.wait(timeout=1):
                        continue
                    jpeg = reconocedor.jpeg
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
        except OSError:
            pass  # se cerro la ventana
        finally:
            ventanas["abiertas"] -= 1
            ventanas["ultima_vez"] = time.monotonic()

    def do_POST(self):
        # Exigir JSON hace que una pagina cualquiera abierta en el
        # navegador no pueda mandarle ordenes a la app.
        if self.headers.get("Content-Type") != "application/json":
            return self.send_error(415)
        largo = int(self.headers.get("Content-Length") or 0)
        datos = json.loads(self.rfile.read(largo) or b"{}")

        if self.path == "/api/categoria":
            try:
                reconocedor.elegir_categoria(datos.get("id"))
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
        elif self.path == "/api/camara":
            if datos.get("buscar"):
                reconocedor.buscar_camaras = True
            else:
                try:
                    reconocedor.elegir_camara(datos.get("id"))
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
        elif self.path == "/api/ajustes":
            ajustes = reconocedor.ajustes
            if "umbral" in datos:
                ajustes["umbral"] = min(0.95, max(0.3, float(datos["umbral"])))
            for clave in ("esqueleto", "espejo"):
                if clave in datos:
                    ajustes[clave] = bool(datos[clave])
        elif self.path == "/api/historial/limpiar":
            reconocedor.historial.clear()
        else:
            return self.send_error(404)
        self._json({"ok": True})


def abrir_ventana(url):
    """Como ventana propia (sin barra del navegador) si esta Edge o Chrome; si no, en el navegador."""
    candidatos = [shutil.which("msedge"), shutil.which("chrome")]
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base:
            candidatos.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
            candidatos.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    for exe in candidatos:
        if exe and os.path.exists(exe):
            subprocess.Popen([exe, f"--app={url}", "--window-size=1280,860"])
            return
    webbrowser.open(url)


def main():
    url = f"http://127.0.0.1:{PUERTO}/"
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Pedido)
    except OSError:
        print("La app ya estaba abierta: te llevo a esa ventana.")
        return abrir_ventana(url)
    servidor.daemon_threads = True
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    print(f"SIGNALIS abierto en {url}")
    print("Para cerrar: cerrá la ventana o apretá Ctrl+C acá.")
    reconocedor.iniciar()
    abrir_ventana(url)

    try:
        while True:
            time.sleep(1)
            cerrada_hace = ventanas["ultima_vez"] and time.monotonic() - ventanas["ultima_vez"]
            if ventanas["abiertas"] == 0 and cerrada_hace and cerrada_hace > ESPERA_SIN_VENTANA_S:
                break
    except KeyboardInterrupt:
        pass
    reconocedor.detener()


if __name__ == "__main__":
    main()
