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
from memory import cargar_memoria, guardar_memoria, cargar_historial_previo, guardar_historial
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
        sistema_completo = SISTEMA.replace('"""', "") + f"\nRecuerdos de sesiones anteriores:\n{recuerdos_str}\n"
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
                response = modelo.generar(contents=historial, config=config)
            except LLMError as e:
                logger.error(f"Error API: {e}")
                print(f"  [ERROR API] {e}")
                break

            if modelo.tiene_tool_calls(response):
                contenido = modelo.extraer_contenido(response)
                if contenido:
                    historial.append(contenido)

                tool_calls = modelo.extraer_tool_calls(response)
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]

                    logger.info(f"[tool] {tool_name}({tool_args})")

                    resultado = ejecutar_tool(tool_name, tool_args)

                    preview = resultado[:200] + ("..." if len(resultado) > 200 else "")
                    logger.debug(f"[resultado {tool_name}] {preview}")

                    historial.append(modelo.crear_mensaje_tool_response(tool_name, resultado))

            else:
                texto = modelo.extraer_texto(response)
                contenido = modelo.extraer_contenido(response)
                if contenido:
                    historial.append(contenido)
                print(f"\ntú > {texto}\n")
                break

        else:
            logger.warning("El agente llego al limite de MAX_ITER sin responder.")
            print("  [aviso] El agente llego al limite de iteraciones.")


if __name__ == "__main__":
    main()
