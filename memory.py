"""
memory.py — Persistencia de recuerdos e historial.

Mejoras respecto a la version anterior:
- Memoria por contexto/proyecto (no solo un diccionario global)
- Busqueda semantica simple sobre recuerdos guardados
- Tags opcionales para categorizar recuerdos
"""

import json
import os
from datetime import datetime

from config import MEMORIA_FILE, HISTORIAL_FILE


# ---------------------------------------------------------------------------
# Estructura de memoria mejorada
# ---------------------------------------------------------------------------
# Formato del archivo:
# {
#   "memoria": {
#     "global": {"clave": "valor"},
#     "contextos": {
#       "default": {"clave": "valor"},
#       "proyecto-x": {"otra_clave": "otro_valor"}
#     }
#   },
#   "tags": {"tag1": ["clave1", "clave2"], ...},
#   "meta": {"ultima_actualizacion": "2026-11-10T12:00:00"}
# }


def _cargar_archivo(path):
    """Carga JSON o devuelve dict vacio."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _guardar_archivo(path, data):
    """Guarda JSON con indentacion."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# API de memoria mejorada
# ---------------------------------------------------------------------------


def cargar_memoria(contexto: str = "default") -> dict:
    """Carga recuerdos para un contexto especifico.

    Args:
        contexto: nombre del contexto ('default', 'proyecto-x', etc.)
                  Si es 'global' carga el namespace global.
    """
    data = _cargar_archivo(MEMORIA_FILE)
    memoria = data.get("memoria", {})

    if contexto == "global":
        return memoria.get("global", {})

    return memoria.get("contextos", {}).get(contexto, {})


def guardar_memoria(memoria: dict, contexto: str = "default"):
    """Guarda recuerdos para un contexto especifico."""
    data = _cargar_archivo(MEMORIA_FILE)
    if "memoria" not in data:
        data["memoria"] = {"global": {}, "contextos": {}}

    if contexto == "global":
        data["memoria"]["global"].update(memoria)
    else:
        if "contextos" not in data["memoria"]:
            data["memoria"]["contextos"] = {}
        data["memoria"]["contextos"][contexto] = memoria

    data["meta"] = {"ultima_actualizacion": datetime.now().isoformat()}
    _guardar_archivo(MEMORIA_FILE, data)


def recordar(clave: str, valor: str, contexto: str = "default", tags: list = None):
    """Guarda un recuerdo con opcion de tags y contexto."""
    memoria = cargar_memoria(contexto)
    memoria[clave] = valor
    guardar_memoria(memoria, contexto)

    # Actualizar indices de tags si se proporcionan
    if tags:
        data = _cargar_archivo(MEMORIA_FILE)
        if "tags" not in data:
            data["tags"] = {}
        for tag in tags:
            tag = tag.lower()
            if tag not in data["tags"]:
                data["tags"][tag] = []
            if clave not in data["tags"][tag]:
                data["tags"][tag].append(clave)
        data["meta"] = {"ultima_actualizacion": datetime.now().isoformat()}
        _guardar_archivo(MEMORIA_FILE, data)


def recuperar(clave: str, contexto: str = "default") -> str:
    """Recupera un recuerdo por su clave."""
    memoria = cargar_memoria(contexto)
    return memoria.get(clave, None)


def listar_recuerdos(contexto: str = "default") -> dict:
    """Lista todos los recuerdos de un contexto."""
    return cargar_memoria(contexto)


def buscar_recuerdos(termino: str, contexto: str = "default") -> list:
    """Busca recuerdos que contengan el termino dado (case-insensitive).

    Devuelve lista de dicts con {'clave': ..., 'valor': ..., 'relevancia': ...}.
    """
    memoria = cargar_memoria(contexto)
    termino_lower = termino.lower()
    resultados = []

    for clave, valor in memoria.items():
        valor_str = str(valor).lower()
        if termino_lower in clave.lower() or termino_lower in valor_str:
            # Calcular relevancia: mas alto si esta en la clave
            relevancia = 2 if termino_lower in clave.lower() else 1
            resultados.append(
                {
                    "clave": clave,
                    "valor": valor,
                    "relevancia": relevancia,
                }
            )

    # Ordenar por relevancia descendente
    resultados.sort(key=lambda x: x["relevancia"], reverse=True)
    return resultados


def borrar_recuerdo(clave: str, contexto: str = "default"):
    """Elimina un recuerdo especifico."""
    memoria = cargar_memoria(contexto)
    if clave in memoria:
        del memoria[clave]
        guardar_memoria(memoria, contexto)


def limpiar_memoria(contexto: str = "default"):
    """Limpia todos los recuerdos de un contexto."""
    data = _cargar_archivo(MEMORIA_FILE)
    if contexto == "global":
        data.setdefault("memoria", {})["global"] = {}
    else:
        data.setdefault("memoria", {}).setdefault("contextos", {}).pop(contexto, None)
    _guardar_archivo(MEMORIA_FILE, data)


# ---------------------------------------------------------------------------
# Historial de conversation
# ---------------------------------------------------------------------------


def cargar_historial_previo() -> list:
    """Carga el historial de conversation previo."""
    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def guardar_historial(historial: list, max_msgs: int = 100):
    """Guarda el historial de conversation, manteniendo las ultimas N mensagens."""
    textos = []
    for msg in historial:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "text") and part.text:
                    textos.append({"role": msg.role, "text": part.text})
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(textos[-max_msgs:], f, ensure_ascii=False, indent=2)
