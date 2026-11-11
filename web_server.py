"""
web_server.py — Interfaz HTTP ligera para el agente.

Uso:
    python web_server.py          # servidor por defecto en puerto 8080
    python web_server.py 9000     # puerto personalizado

Endpoints:
    POST /chat      → {"prompt": "tu mensaje"} → {"response": "respuesta del agente"}
    GET  /health    → {"status": "ok"}
    GET  /          → página HTML simple
"""

import json
import os
import sys
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Importaciones del proyecto
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import LLM, LLMError
from config import SISTEMA, logger
from tools import TOOL_FUNCTIONS
from schema import TOOLS_SCHEMA

# ---------------------------------------------------------------------------
# Estado global del agente (thread-safe)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_historial = []
_llm_instance = None


def _init_agent():
    """Inicializa el LLM y carga memoria previa."""
    global _llm_instance, _historial

    # .env tiene prioridad sobre variables de entorno
    _vals = {}
    try:
        from dotenv import dotenv_values

        _vals = dotenv_values()
    except Exception:
        pass
    api_key = (
        _vals.get("GEMINI_API_KEY")
        or _vals.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY o GOOGLE_API_KEY")

    _llm_instance = LLM(
        proveedor="gemini",
        api_key=api_key,
        model="gemini-3.8-flash",
        max_retries=1,
        base_delay=1.0,
        timeout_secs=float(os.environ.get("LLM_TIMEOUT_SECS", "300")),
    )

    # Cargar historial previo
    from memory import cargar_historial_previo, cargar_memoria

    memoria = cargar_memoria()
    sistema_completo = SISTEMA
    if memoria:
        recuerdos_str = "\n".join(f"- {k}: {v}" for k, v in memoria.items())
        sistema_completo += f"\nRecuerdos de sesiones anteriores:\n{recuerdos_str}\n"

    textos_previos = cargar_historial_previo()
    _historial = []
    if textos_previos:
        for t in textos_previos:
            if "text" in t and t["text"]:
                _historial.append(_llm_instance.crear_mensaje(t["role"], t["text"]))

    return sistema_completo


AGENTE_CONFIG = {
    "system_instruction": "",
    "tools": TOOLS_SCHEMA,
}


def _ejecutar_chat(prompt: str) -> str:
    """Procesa un mensaje del usuario y devuelve la respuesta."""
    global _historial

    if _llm_instance is None:
        _init_agent()

    with _lock:
        _historial.append(_llm_instance.crear_mensaje_usuario(prompt))

        MAX_ITER = 10
        iteraciones = 0
        respuesta_final = ""

        while iteraciones < MAX_ITER:
            iteraciones += 1
            try:
                stream = _llm_instance.generar_streaming(
                    contents=_historial, config=AGENTE_CONFIG
                )
            except LLMError as e:
                logger.error(f"Error API: {e}")
                return f"[ERROR API] {e}"

            texto_completo = ""
            tiene_tool_calls = False

            try:
                for chunk in stream:
                    try:
                        parts = chunk.candidates[0].content.parts
                        if parts:
                            for part in parts:
                                if (
                                    hasattr(part, "function_call")
                                    and part.function_call
                                ):
                                    tiene_tool_calls = True
                    except (IndexError, AttributeError, TypeError):
                        pass

                    try:
                        partes = chunk.candidates[0].content.parts
                        if partes:
                            for parte in partes:
                                if hasattr(parte, "text") and parte.text:
                                    texto_completo += parte.text
                    except (IndexError, AttributeError, TypeError):
                        pass
            except Exception as e:
                # Errores durante streaming (503, timeouts, etc.)
                error_msg = str(e)
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    return "[aviso] Gemini está con alta demanda temporal. Probá de nuevo en unos minutos."
                elif "402" in error_msg or "credits" in error_msg.lower():
                    return "[error] Créditos agotados. Verificá tu cuenta en Google AI Studio."
                elif "404" in error_msg or "NOT_FOUND" in error_msg:
                    return "[error] Modelo no disponible. Contactá al administrador."
                else:
                    logger.error(f"Error en streaming: {e}")
                    return f"[error] Error inesperado: {error_msg[:200]}"

            if tiene_tool_calls:
                contenido = None
                try:
                    contenido = stream.candidates[0].content
                except (IndexError, AttributeError):
                    pass
                if contenido:
                    _historial.append(contenido)

                tool_calls = []
                try:
                    parts = stream.candidates[0].content.parts
                    if parts:
                        for part in parts:
                            if hasattr(part, "function_call") and part.function_call:
                                tool_calls.append(
                                    {
                                        "name": part.function_call.name,
                                        "args": dict(part.function_call.args)
                                        if part.function_call.args
                                        else {},
                                    }
                                )
                except (IndexError, AttributeError, TypeError):
                    pass

                try:
                    for tc in tool_calls:
                        resultado = str(TOOL_FUNCTIONS[tc["name"]](**tc["args"]))
                        _historial.append(
                            _llm_instance.crear_mensaje_tool_response(
                                tc["name"], resultado
                            )
                        )
                except Exception as e:
                    logger.error(f"Error ejecutando herramienta: {e}")
                    texto_completo = f"[error ejecutando herramienta] {e}"

            elif texto_completo:
                respuesta_final = texto_completo.strip()
                break

        if not respuesta_final:
            respuesta_final = "[aviso] No pude generar una respuesta."

        return respuesta_final


# ---------------------------------------------------------------------------
# Handler HTTP
# ---------------------------------------------------------------------------
class AgenteHandler(BaseHTTPRequestHandler):
    """Handler para el servidor HTTP del agente."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json_response({"status": "ok"})
        elif parsed.path == "/":
            self._serve_index()
        else:
            self._not_found()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/chat":
            self._handle_chat()
        else:
            self._not_found()

    def _handle_chat(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            prompt = data.get("prompt", "").strip()
            if not prompt:
                self._json_response({"error": "prompt vacio"}, 400)
                return

            # Ejecutar en hilo separado con timeout para que el servidor
            # nunca se cuelgue si Gemini no responde
            resultado = [None]
            excepcion = [None]

            def ejecutar():
                try:
                    resultado[0] = _ejecutar_chat(prompt)
                except Exception as e:
                    excepcion[0] = e

            hilo = threading.Thread(target=ejecutar, daemon=True)
            hilo.start()
            chat_timeout = int(os.environ.get("CHAT_TIMEOUT_SECS", "120"))
            hilo.join(timeout=chat_timeout)  # max configurable (default 120s)

            if excepcion[0]:
                raise excepcion[0]
            if resultado[0] is None:
                self._json_response(
                    {
                        "error": f"La solicitud excedió el tiempo límite ({chat_timeout}s)"
                    },
                    504,
                )
                return

            self._json_response({"response": resultado[0]})
        except Exception as e:
            logger.exception("Error en /chat")
            try:
                self._json_response({"error": str(e)}, 500)
            except Exception:
                pass  # conexión ya cerrada por el cliente

    def _serve_index(self):
        html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agente 3573b4n</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #1a1a2e; color: #eee; height: 100vh; display: flex; flex-direction: column; }
#chat { flex: 1; overflow-y: auto; padding: 20px; }
.msg { margin-bottom: 16px; max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
.msg.user { background: #16213e; align-self: flex-end; margin-left: auto; }
.msg.agent { background: #0f3460; align-self: flex-start; }
#input-area { display: flex; padding: 16px; gap: 8px; background: #16213e; }
#input-area input { flex: 1; padding: 12px; border: none; border-radius: 8px; background: #1a1a2e; color: #eee; font-size: 16px; }
#input-area button { padding: 12px 24px; border: none; border-radius: 8px; background: #e94560; color: white; font-size: 16px; cursor: pointer; }
#input-area button:hover { background: #c73652; }
.loading { opacity: 0.5; font-style: italic; }
</style>
</head>
<body>
<div id="chat"></div>
<div id="input-area">
<input type="text" id="user-input" placeholder="Escribí tu mensaje..." autofocus>
<button onclick="enviar()">Enviar</button>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('user-input');

function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function enviar() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMsg('user', text);
    const loading = document.createElement('div');
    loading.className = 'msg agent loading';
    loading.textContent = 'Pensando...';
    chat.appendChild(loading);
    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt: text})
        });
        const data = await res.json();
        loading.remove();
        if (data.response) addMsg('agent', data.response);
        else if (data.error) addMsg('agent', '[ERROR] ' + data.error);
    } catch(e) {
        loading.remove();
        addMsg('agent', '[ERROR] No se pudo conectar al servidor');
    }
}

input.addEventListener('keydown', e => { if (e.key === 'Enter') enviar(); });
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _json_response(self, data, status=200):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass  # cliente cerró la conexión

    def _not_found(self):
        self._json_response({"error": "no encontrado"}, 404)

    def log_message(self, format, *args):
        logger.info(f"HTTP {args[0]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(port=8080):
    print(f"Iniciando servidor en http://localhost:{port}")
    print("  Abre http://localhost:{port} en tu navegador")
    print("  POST /chat para usar via API")
    print("  Ctrl+C para detener")
    server = HTTPServer(("0.0.0.0", port), AgenteHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
