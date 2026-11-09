"""
AGENTE 3573b4n
==============

Agente conversacional con Gemini 2.5 Flash + herramientas.
Puede leer/escribir archivos, ejecutar comandos, buscar texto,
recordar información entre sesiones, y mucho más.

EL AGENTE ES UN LOOP (while True):
  usuario pide algo
  -> el modelo decide si llama una tool o responde
  -> si llama tool -> ejecutamos la tool -> le damos el resultado al modelo
  -> el modelo decide de nuevo
  -> repite hasta que decide responder al usuario

No es magia. Es un bucle.

Instalacion:
  pip install google-genai

Uso:
  Setea tu API key como variable de entorno:
    Windows PowerShell:  $env:GEMINI_API_KEY = "tu-key-aqui"
    Windows CMD:         set GEMINI_API_KEY=tu-key-aqui

  Despues:
    python agente.py
"""

import os
import sys

from llm import LLM, LLMError

from config import logger, SISTEMA
from memory import (
    cargar_memoria,
    guardar_memoria,
    cargar_historial_previo,
    guardar_historial,
)
from tools import (
    TOOL_FUNCTIONS,
    WHITELIST_COMANDOS,
    BLACKLIST_PELIGROS,
    _comando_permitido,
    leer_archivo,
    listar_directorio,
    escribir_archivo,
    correr_comando,
    buscar_texto,
    recordar,
    recuperar,
    listar_recuerdos,
    ver_logs,
)
from schema import TOOLS_SCHEMA


# ---------------------------------------------------------------------------
# API key y modelo
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("ERROR: Falta la variable de entorno GEMINI_API_KEY o GOOGLE_API_KEY")
    print("  PowerShell: $env:GEMINI_API_KEY = 'tu-key-aqui'")
    print("  CMD:        set GEMINI_API_KEY=tu-key-aqui")
    sys.exit(1)

MODEL_NOMBRE = "gemini-2.5-flash"
try:
    modelo = LLM(proveedor="gemini", api_key=API_KEY, model=MODEL_NOMBRE)
except LLMError as e:
    print(f"ERROR al inicializar el modelo: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Ejecutor de tools
# ---------------------------------------------------------------------------
def ejecutar_tool(nombre: str, args: dict) -> str:
    func = TOOL_FUNCTIONS.get(nombre)
    if not func:
        return f"ERROR: tool '{nombre}' no existe"
    try:
        return str(func(**args))
    except TypeError as e:
        return f"ERROR: argumentos invalidos para '{nombre}': {e}"


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def main():
    memoria = cargar_memoria()
    if memoria:
        recuerdos_str = "\n".join(f"- {k}: {v}" for k, v in memoria.items())
        sistema_completo = (
            SISTEMA.replace('"""', "")
            + f"\nRecuerdos de sesiones anteriores:\n{recuerdos_str}\n"
        )
    else:
        sistema_completo = SISTEMA

    textos_previos = cargar_historial_previo()
    historial = []
    if textos_previos:
        for t in textos_previos:
            if "text" in t and t["text"]:
                historial.append(modelo.crear_mensaje(t["role"], t["text"]))

    print("=" * 60)
    print("  AGENTE 3573b4n (Gemini 2.5 Flash)")
    if memoria:
        print(f"  Recuerdos cargados: {len(memoria)} items")
    if textos_previos:
        print(f"  Historial cargado: {len(textos_previos)} mensajes previos")
    print("  Escribi 'salir' para terminar")
    print("=" * 60)
    print()

    config = {
        "system_instruction": sistema_completo,
        "tools": TOOLS_SCHEMA,
    }

    while True:
        try:
            user_input = input("ahora te toca a ti > ").strip()
        except (EOFError, KeyboardInterrupt):
            guardar_historial(historial)
            print("\nChau!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("salir", "exit", "quit"):
            guardar_historial(historial)
            print("Chau!")
            break

        historial.append(modelo.crear_mensaje_usuario(user_input))

        iteraciones = 0
        MAX_ITER = 10

        while iteraciones < MAX_ITER:
            iteraciones += 1

            try:
                # Usar streaming para respuesta incremental
                stream = modelo.generar_streaming(contents=historial, config=config)
            except LLMError as e:
                logger.error(f"Error API: {e}")
                print(f"\n  [ERROR API] {e}\n")
                break

            texto_completo = ""
            tiene_tool_calls = False

            for chunk in stream:
                # Verificar si hay function calls en este chunk
                try:
                    parts = chunk.candidates[0].content.parts
                    if parts:
                        for part in parts:
                            if hasattr(part, "function_call") and part.function_call:
                                tiene_tool_calls = True
                except (IndexError, AttributeError, TypeError):
                    pass

                # Extraer texto del chunk
                try:
                    partes = chunk.candidates[0].content.parts
                    if partes:
                        for parte in partes:
                            if hasattr(parte, "text") and parte.text:
                                texto_completo += parte.text
                                print(parte.text, end="", flush=True)
                except (IndexError, AttributeError, TypeError):
                    pass

            print()  # salto de linea despues del streaming

            if tiene_tool_calls:
                # Reconstruir el contenido completo para el historial
                contenido = None
                try:
                    contenido = stream.candidates[0].content
                except (IndexError, AttributeError):
                    pass

                if contenido:
                    historial.append(contenido)

                # Extraer los tool calls del stream completo
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

                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]

                    logger.info(f"[tool] {tool_name}({tool_args})")

                    resultado = ejecutar_tool(tool_name, tool_args)

                    preview = resultado[:200] + ("..." if len(resultado) > 200 else "")
                    logger.debug(f"[resultado {tool_name}] {preview}")

                    historial.append(
                        modelo.crear_mensaje_tool_response(tool_name, resultado)
                    )

            elif texto_completo:
                print(f"\ntú > {texto_completo.strip()}\n")
                break

        else:
            logger.warning("El agente llego al limite de MAX_ITER sin responder.")
            print("  [aviso] El agente llego al limite de iteraciones.")


if __name__ == "__main__":
    main()
