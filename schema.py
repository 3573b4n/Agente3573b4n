"""
Schema de herramientas para Gemini (function_declarations).

Este módulo genera automáticamente el schema a partir de las funciones
en tools.TOOL_FUNCTIONS, así que no hace falta mantener schema.py en paralelo.
"""

import inspect
from typing import get_type_hints, get_origin
from tools import TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# Mapeo de tipos Python -> JSON Schema
# ---------------------------------------------------------------------------
TIPO_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_a_json_tipo(tipo) -> str:
    """Convierte un tipo Python a su equivalente en JSON Schema."""
    if tipo in TIPO_MAP:
        return TIPO_MAP[tipo]
    origin = get_origin(tipo)
    if origin and origin in TIPO_MAP:
        return TIPO_MAP[origin]
    return "string"  # fallback


def _generar_schema_tool(func) -> dict:
    """Genera el schema Gemini para una sola herramienta."""
    nombre = func.__name__
    doc = func.__doc__ or ""
    descripcion = doc.strip().split("\n")[0].strip()

    sig = inspect.signature(func)
    properties = {}
    required = []

    for nombre_param, parametro in sig.parameters.items():
        if nombre_param == "self":
            continue

        try:
            hints = get_type_hints(func)
            tipo = hints.get(nombre_param, str)
            json_tipo = _python_a_json_tipo(tipo)
        except (TypeError, NameError):
            json_tipo = "string"

        propiedades_param = {"type": json_tipo}

        if parametro.default is not inspect.Parameter.empty:
            propiedades_param["description"] = f"Default: {parametro.default}"
        else:
            required.append(nombre_param)

        properties[nombre_param] = propiedades_param

    return {
        "name": nombre,
        "description": descripcion,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required if required else [],
        },
    }


def generar_tools_schema() -> list:
    """Genera todo el TOOLS_SCHEMA automáticamente desde TOOL_FUNCTIONS."""
    functions = []
    for nombre, func in sorted(TOOL_FUNCTIONS.items()):
        functions.append(_generar_schema_tool(func))
    return [{"function_declarations": functions}]


# Schema generado (se usa en agente.py)
TOOLS_SCHEMA = generar_tools_schema()
