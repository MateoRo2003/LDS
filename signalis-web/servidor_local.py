"""
Sirve esta carpeta en http://127.0.0.1:8790/ para probar la version web
en la propia computadora, sin publicarla. (El navegador solo deja usar
la camara desde https o desde esta misma maquina.)

Uso:
    python servidor_local.py
"""
import functools
import http.server
import os

PUERTO = 8790


class Pedido(http.server.SimpleHTTPRequestHandler):
    # Windows a veces declara mal estos tipos, y el navegador se niega a
    # cargar un modulo o un .wasm con el tipo equivocado.
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".wasm": "application/wasm",
        ".json": "application/json",
        ".task": "application/octet-stream",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    carpeta = os.path.dirname(os.path.abspath(__file__))
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), functools.partial(Pedido, directory=carpeta))
    print(f"SIGNALIS web en http://127.0.0.1:{PUERTO}/  (Ctrl+C para cerrar)")
    servidor.serve_forever()
