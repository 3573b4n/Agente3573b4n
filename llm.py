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
import time
import random
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

    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-3.8-flash",
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout_secs: float = 300.0,
    ):
        # Si no pasamos key, la buscamos en variable de entorno
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise LLMError(
                "Falta GEMINI_API_KEY o GOOGLE_API_KEY en variables de entorno"
            )

        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout_secs = timeout_secs

        # Import laziness: solo importamos google.genai si este provider se usa
        try:
            from google import genai
            from google.genai import types

            self.genai = genai
            self.types = types
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={"timeout": int(self.timeout_secs * 1000)},
            )
        except ImportError as e:
            raise LLMError(
                "Falta instalar google-genai: pip install google-genai"
            ) from e

    def _is_retryable_error(self, exception: Exception) -> tuple[bool, str]:
        """Determina si una excepcion puede ser reintentada y por que."""
        msg = str(exception).lower()

        # Rate limiting — 429 / quota exceeded
        if any(kw in msg for kw in ["429", "too many requests", "quota", "rate limit"]):
            return True, "rate_limit"

        # Server errors — 5xx
        if any(kw in msg for kw in ["500", "502", "503", "504"]):
            return True, "server_error"

        # Connection errors / timeouts
        if any(
            kw in msg
            for kw in [
                "timeout",
                "connection",
                "temporarily",
                "unavailable",
                "service unavailable",
                "network",
                "socket",
            ]
        ):
            return True, "connection"

        # Generic retryable patterns
        if any(kw in msg for kw in ["overloaded", "backoff", "throttl"]):
            return True, "overloaded"

        return False, ""

    def _wait_before_retry(self, attempt: int, reason: str) -> float:
        """Calcula el tiempo de espera con exponential backoff + jitter.

        Estrategia por tipo de error:
          - rate_limit: backoff mas agresivo (1s → 2s → 4s) porque Gemini
            puede tardar en resetear el contador.
          - server_error: backoff normal (1s → 2s → 4s).
          - connection: backoff rapido (0.5s → 1s → 2s) porque suele ser
            temporal y no penaliza esperar menos.
        """
        # Factor base segun tipo de error
        if reason == "rate_limit":
            base = self.base_delay * 2
        elif reason == "connection":
            base = self.base_delay * 0.5
        else:
            base = self.base_delay

        # Exponential backoff: base * 2^(attempt-1)
        delay = base * (2 ** (attempt - 1))

        # Jitter aleatorio +/- 20% para evitar thundering herd
        jitter = delay * 0.2 * (2 * random.random() - 1)
        delay += jitter

        # Cap a 60 segundos maximo (mas generoso que antes)
        delay = min(delay, 60.0)

        logger = None
        try:
            from config import logger
        except ImportError:
            pass

        if logger:
            logger.info(
                f"Reintento {attempt}/{self.max_retries} ({reason}) en {delay:.1f}s"
            )

        time.sleep(delay)
        return delay

    def generar(self, contents, config):
        """
        Llama al modelo de Gemini con el historial y la config.
        Devuelve el objeto response crudo de google-genai.
        Con reintentos automaticos ante errores transitorios.

        Estrategia de retry:
          - Detecta tipo de error (rate_limit, server_error, connection)
          - Aplica backoff diferenciado por tipo
          - Maximo max_retries intentos con delay creciente + jitter
        """
        genai_config = self.types.GenerateContentConfig(
            system_instruction=config.get("system_instruction", ""),
            tools=config.get("tools", []),
        )

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=genai_config,
                )
                return response
            except Exception as e:
                last_exception = e
                is_retryable, reason = self._is_retryable_error(e)

                if not is_retryable or attempt >= self.max_retries:
                    break

                self._wait_before_retry(attempt, reason)

        raise LLMError(
            f"Error llamando a Gemini despues de {self.max_retries} intentos: {last_exception}"
        ) from last_exception

    def generar_streaming(self, contents, config):
        """
        Llama al modelo de Gemini con streaming.
        Devuelve un iterable que emite chunks parciales mientras se genera la respuesta.
        Con reintentos automaticos ante errores transitorios.

        Estrategia de retry:
          - Detecta tipo de error (rate_limit, server_error, connection)
          - Aplica backoff diferenciado por tipo
          - Maximo max_retries intentos con delay creciente + jitter
        """
        genai_config = self.types.GenerateContentConfig(
            system_instruction=config.get("system_instruction", ""),
            tools=config.get("tools", []),
        )

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                stream = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=genai_config,
                )
                return stream
            except Exception as e:
                last_exception = e
                is_retryable, reason = self._is_retryable_error(e)

                if not is_retryable or attempt >= self.max_retries:
                    break

                self._wait_before_retry(attempt, reason)

        raise LLMError(
            f"Error llamando a Gemini (streaming) despues de {self.max_retries} intentos: {last_exception}"
        ) from last_exception

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
                tool_calls.append(
                    {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args)
                        if part.function_call.args
                        else {},
                        "raw_part": part,  # necesitamos el part crudo para el historial
                    }
                )
        return tool_calls

    def tiene_tool_calls(self, response) -> bool:
        """True si la respuesta tiene llamadas a tools."""
        try:
            parts = response.candidates[0].content.parts
            if parts is None:
                return False
            return any(hasattr(p, "function_call") and p.function_call for p in parts)
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
            parts=[
                self.types.Part.from_function_response(
                    name=tool_name,
                    response={"result": resultado},
                )
            ],
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

    def __init__(
        self,
        proveedor: str = "gemini",
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout_secs: float = 90.0,
        **kwargs,
    ):
        self.proveedor_nombre = proveedor
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout_secs = timeout_secs

        if proveedor == "gemini":
            self._impl = GeminiProvider(
                max_retries=max_retries,
                base_delay=base_delay,
                timeout_secs=timeout_secs,
                **kwargs,
            )
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

    def generar_streaming(self, contents, config):
        return self._impl.generar_streaming(contents, config)


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
        print(
            f"  API key: {modelo._impl.api_key[:10]}...{(modelo._impl.api_key or '')[-4:]}"
        )
    except LLMError as e:
        print(f"ERROR: {e}")
