import json
import os

from config import MEMORIA_FILE, HISTORIAL_FILE


def cargar_memoria() -> dict:
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def guardar_memoria(memoria: dict):
    with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def cargar_historial_previo() -> list:
    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def guardar_historial(historial: list, max_msgs: int = 100):
    textos = []
    for msg in historial:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "text") and part.text:
                    textos.append({"role": msg.role, "text": part.text})
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(textos[-max_msgs:], f, ensure_ascii=False, indent=2)
