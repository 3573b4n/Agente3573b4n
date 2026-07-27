"""
LLM Wrapper - Abstraccion del proveedor de modelos
===================================================

Esto separa al agente (agente.py) del proveedor de LLM (Gemini, Claude, etc).

El agente llama a:
    from llm import LLM
    modelo = LLM()
    respuesta = modelo.generar(historial, config)

Y no le importa si atras estamos usando Gemini, Claude o OpenAI.

Uso:
    from llm import LLM

    # Usar Gemini (default, gratis con Google AI Studio)
    modelo = LLM(proveedor="gemini")

    # Usar otro (cuando lo implementemos)
    # modelo = LLM(proveedor="claude")

    # Generar respuesta
    response = modelo.generar(contents=historial, config=config)
    texto = modelo.extraer_texto(response)
    tool_calls = modelo.extraer_tool_calls(response)
"""

import os
from typing import Any

# ---------------------------------------------------------------------------
# Excepciones custom
# ---------------------------------------------------------------------------
class LLMError(Exception):
    """Error generico del wrapper de LLM."""
    pass

# ---------------------------------------------------------------------------
# Implementacion de cada proveedor
# ---------------------------------------------------------------------------
class GeminiProvider:
    """
    Implementacion para Google Gemini usando google-genai.
    Este es el proveedor que ya venimos usando.
    """

    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        # Si no pasamos key, la buscamos en variable de entorno
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise LLMError("Falta GEMINI_API_KEY o GOOGLE_API_KEY en variables de entorno")

        self.model = model

        # Import laziness: solo importamos google.genai si este provider se usa
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=self.api_key)
        except ImportError as e:
            raise LLMError("Falta instalar google-genai: pip install google-genai") from e

    def generar(self, contents, config):
        """
        Llama al modelo de Gemini con el historial y la config.
        Devuelve el objeto response crudo de google-genai.
        """
        # La config que pasamos es un dict con system_instruction y tools
        # Hay que convertirlo al formato que espera Gemini.
        genai_config = self.types.GenerateContentConfig(
            system_instruction=config.get("system_instruction", ""),
            tools=config.get("tools", []),
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=genai_config,
            )
            return response
        except Exception as e:
            raise LLMError(f"Error llamando a Gemini: {e}") from e

    def extraer_texto(self, response) -> str:
        """Extrae el texto de una respuesta de Gemini."""
        try:
            parts = response.candidates[0].content.parts
            if parts is None:
                return ""
            return parts[0].text
        except (IndexError, AttributeError, TypeError):
            return ""

    def extraer_tool_calls(self, response) -> list:
        """
        Extrae las llamadas a tools de una respuesta de Gemini.
        Devuelve una lista de dicts: [{"name": ..., "args": ...}, ...]
        """
        tool_calls = []
        try:
            parts = response.candidates[0].content.parts
            if parts is None:
                return tool_calls
        except (IndexError, AttributeError, TypeError):
            return tool_calls

        for part in parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args) if part.function_call.args else {},
                    "raw_part": part,  # necesitamos el part crudo para el historial
                })
        return tool_calls

    def tiene_tool_calls(self, response) -> bool:
        """True si la respuesta tiene llamadas a tools."""
        try:
            parts = response.candidates[0].content.parts
            if parts is None:
                return False
            return any(
                hasattr(p, "function_call") and p.function_call
                for p in parts
            )
        except (IndexError, AttributeError, TypeError):
            return False

    def extraer_contenido(self, response):
        """Devuelve el objeto Content crudo para agregar al historial."""
        try:
            return response.candidates[0].content
        except (IndexError, AttributeError):
            return None

    def crear_mensaje_usuario(self, texto: str):
        """Crea un Content con role='user' y texto."""
        return self.types.Content(
            role="user",
            parts=[self.types.Part.from_text(text=texto)],
        )

    def crear_mensaje_tool_response(self, tool_name: str, resultado: str):
        """Crea un Content con role='user' y function_response."""
        return self.types.Content(
            role="user",
            parts=[self.types.Part.from_function_response(
                name=tool_name,
                response={"result": resultado},
            )],
        )

    def crear_mensaje(self, role: str, texto: str):
        """Crea un Content con role y texto genericos."""
        return self.types.Content(
            role=role,
            parts=[self.types.Part.from_text(text=texto)],
        )


# ---------------------------------------------------------------------------
# Factory: seleccionar el proveedor segun el nombre
# ---------------------------------------------------------------------------
class LLM:
    """
    Interfaz unificada para multiples proveedores de LLM.

    Uso:
        modelo = LLM(proveedor="gemini")
        response = modelo.generar(contents, config)
    """

    def __init__(self, proveedor: str = "gemini", **kwargs):
        self.proveedor_nombre = proveedor

        if proveedor == "gemini":
            self._impl = GeminiProvider(**kwargs)
        # Cuando implementemos otros:
        # elif proveedor == "claude":
        #     self._impl = ClaudeProvider(**kwargs)
        # elif proveedor == "openai":
        #     self._impl = OpenAIProvider(**kwargs)
        else:
            raise LLMError(f"Proveedor '{proveedor}' no soportado. Disponibles: gemini")

    # Passthrough a la implementacion
    def generar(self, contents, config):
        return self._impl.generar(contents, config)

    def extraer_texto(self, response) -> str:
        return self._impl.extraer_texto(response)

    def extraer_tool_calls(self, response) -> list:
        return self._impl.extraer_tool_calls(response)

    def tiene_tool_calls(self, response) -> bool:
        return self._impl.tiene_tool_calls(response)

    def extraer_contenido(self, response):
        return self._impl.extraer_contenido(response)

    def crear_mensaje(self, role: str, texto: str):
        return self._impl.crear_mensaje(role, texto)

    def crear_mensaje_usuario(self, texto: str):
        return self._impl.crear_mensaje_usuario(texto)

    def crear_mensaje_tool_response(self, tool_name: str, resultado: str):
        return self._impl.crear_mensaje_tool_response(tool_name, resultado)


# ---------------------------------------------------------------------------
# Test rapido para verificar que el wrapper funciona
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Test del wrapper LLM")
    print("=" * 40)

    try:
        modelo = LLM(proveedor="gemini")
        print("OK: GeminiProvider inicializado")
        print(f"  Modelo: {modelo._impl.model}")
        print(f"  API key: {modelo._impl.api_key[:10]}...{(modelo._impl.api_key or '')[-4:]}")
    except LLMError as e:
        print(f"ERROR: {e}")
