import os

from config import logger, _log_file
from memory import cargar_memoria, guardar_memoria


# ---------------------------------------------------------------------------
# Seguridad de correr_comando
# ---------------------------------------------------------------------------
WHITELIST_COMANDOS = [
    "python",
    "python3",
    "pip",
    "dir",
    "ls",
    "type",
    "cat",
    "echo",
    "mkdir",
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git show",
    "git ls-files",
]

BLACKLIST_PELIGROS = [
    "rm -rf",
    "del /s",
    "del /q",
    "rmdir /s",
    "rd /s",
    "format",
    "shutdown",
    "restart",
    "> /dev/sda",
    "mkfs",
]


def _comando_permitido(comando: str) -> tuple[bool, str]:
    cmd_lower = comando.strip().lower()
    if not cmd_lower:
        return False, "comando vacio"
    for peligroso in BLACKLIST_PELIGROS:
        if peligroso in cmd_lower:
            return False, f"comando peligroso detectado: '{peligroso}'"
    for permitido in WHITELIST_COMANDOS:
        if cmd_lower.startswith(permitido):
            resto = cmd_lower[len(permitido):]
            if resto == "" or resto[0] in (" ", "\t"):
                return True, "OK"
    return False, f"comando '{comando}' no esta en la whitelist"


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------

def leer_archivo(ruta: str) -> str:
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"ERROR: No existe el archivo '{ruta}'"
    except Exception as e:
        return f"ERROR al leer '{ruta}': {e}"


def listar_directorio(ruta: str = ".") -> str:
    try:
        entries = os.listdir(ruta)
        dirs = [d + "/" for d in entries if os.path.isdir(os.path.join(ruta, d))]
        files = [f for f in entries if not os.path.isdir(os.path.join(ruta, f))]
        if not dirs and not files:
            return f"(directorio vacio: {ruta})"
        return "\n".join(dirs + files)
    except Exception as e:
        return f"ERROR al listar '{ruta}': {e}"


def escribir_archivo(ruta: str, contenido: str) -> str:
    try:
        directorio_padre = os.path.dirname(ruta)
        if directorio_padre and not os.path.exists(directorio_padre):
            os.makedirs(directorio_padre, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"OK: archivo '{ruta}' escrito ({len(contenido)} caracteres)"
    except Exception as e:
        return f"ERROR al escribir '{ruta}': {e}"


def correr_comando(comando: str, timeout: int = 30) -> str:
    permitido, motivo = _comando_permitido(comando)
    if not permitido:
        return f"ERROR: comando rechazado. Motivo: {motivo}"
    import subprocess
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        salida = ""
        if resultado.stdout:
            salida += resultado.stdout
        if resultado.stderr:
            salida += f"\n[STDERR]\n{resultado.stderr}"
        MAX_SALIDA = 4000
        if len(salida) > MAX_SALIDA:
            salida = salida[:MAX_SALIDA] + f"\n[... truncado, {len(salida) - MAX_SALIDA} caracteres mas]"
        return f"[exit code {resultado.returncode}]\n{salida}"
    except subprocess.TimeoutExpired:
        return f"ERROR: el comando supero el timeout de {timeout} segundos y fue cancelado."
    except Exception as e:
        return f"ERROR al ejecutar '{comando}': {e}"


def buscar_texto(pattern: str, ruta: str = ".", extension: str = None) -> str:
    import re
    import glob
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: regex invalido '{pattern}': {e}"
    if extension:
        search_path = os.path.join(ruta, "**", extension)
        archivos = glob.glob(search_path, recursive=True)
    else:
        archivos = []
        for root, dirs, files in os.walk(ruta):
            for f in files:
                archivos.append(os.path.join(root, f))
    if not archivos:
        return f"(sin archivos en {ruta}" + (f" con extension {extension}" if extension else "") + ")"
    resultados = []
    MAX_RESULTADOS = 50
    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                for i, linea in enumerate(f, 1):
                    if regex.search(linea):
                        contenido = linea.rstrip("\n")
                        if len(contenido) > 200:
                            contenido = contenido[:200] + "..."
                        resultados.append(f"{archivo}:{i}:{contenido}")
                        if len(resultados) >= MAX_RESULTADOS:
                            break
                if len(resultados) >= MAX_RESULTADOS:
                    break
        except (UnicodeDecodeError, PermissionError):
            continue
        except Exception as e:
            resultados.append(f"{archivo}:ERROR:{e}")
    if not resultados:
        return f"(sin coincidencias para '{pattern}' en {ruta})"
    salida = "\n".join(resultados)
    if len(resultados) >= MAX_RESULTADOS:
        salida += f"\n[... truncado, maximo {MAX_RESULTADOS} resultados]"
    return salida


def recordar(clave: str, valor: str) -> str:
    memoria = cargar_memoria()
    memoria[clave] = valor
    guardar_memoria(memoria)
    return f"OK: recordado '{clave}' = '{valor}'"


def recuperar(clave: str) -> str:
    memoria = cargar_memoria()
    valor = memoria.get(clave)
    if valor is None:
        return f"(no tengo nada recordado sobre '{clave}')"
    return f"{clave}: {valor}"


def listar_recuerdos() -> str:
    memoria = cargar_memoria()
    if not memoria:
        return "(no tengo recuerdos guardados)"
    return "\n".join(f"  {k}: {v}" for k, v in memoria.items())


def ver_logs(lineas: int = 20) -> str:
    try:
        with open(_log_file, "r", encoding="utf-8") as f:
            todas = f.readlines()
        ultimas = todas[-lineas:]
        return "".join(ultimas)
    except FileNotFoundError:
        return "(aun no hay logs)"
    except Exception as e:
        return f"ERROR al leer logs: {e}"


TOOL_FUNCTIONS = {
    "leer_archivo": leer_archivo,
    "listar_directorio": listar_directorio,
    "escribir_archivo": escribir_archivo,
    "correr_comando": correr_comando,
    "buscar_texto": buscar_texto,
    "recordar": recordar,
    "recuperar": recuperar,
    "listar_recuerdos": listar_recuerdos,
    "ver_logs": ver_logs,
}
