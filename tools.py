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


def fecha_hora(zona: str = "Europe/Madrid") -> str:
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(zona)
    except (ImportError, KeyError):
        try:
            import pytz
            tz = pytz.timezone(zona)
        except ImportError:
            return f"ERROR: zona '{zona}' no disponible (sin zoneinfo ni pytz)"
    ahora = datetime.now(tz)
    return (
        f"Fecha: {ahora.strftime('%A, %d de %B de %Y')}\n"
        f"Hora: {ahora.strftime('%H:%M:%S')}\n"
        f"Zona: {zona}\n"
        f"ISO:  {ahora.isoformat()}"
    )


def tree(ruta: str = ".", max_nivel: int = 7) -> str:
    from pathlib import Path

    raiz = Path(ruta)
    if not raiz.is_dir():
        return f"ERROR: '{ruta}' no es un directorio"
    if max_nivel < 1:
        return f"ERROR: max_nivel debe ser >= 1"

    rama = "+-- "
    final = "\\-- "
    tubo = "|   "
    espacio = "    "

    lineas = [f"{raiz.resolve()}/"]

    def _recorrer(directorio: Path, nivel: int, prefijo: str):
        if nivel > max_nivel:
            lineas.append(f"{prefijo}{final}...")
            return

        entradas = sorted(
            directorio.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )

        for i, entrada in enumerate(entradas):
            es_ultimo = i == len(entradas) - 1
            conector = final if es_ultimo else rama

            if entrada.is_dir():
                lineas.append(f"{prefijo}{conector}{entrada.name}/")
                nuevo = espacio if es_ultimo else tubo
                _recorrer(entrada, nivel + 1, prefijo + nuevo)
            else:
                lineas.append(f"{prefijo}{conector}{entrada.name}")

    _recorrer(raiz, 0, "")
    return "\n".join(lineas)


def descargar_url(url: str, timeout: int = 15) -> str:
    import requests

    if not url.startswith(("http://", "https://")):
        return f"ERROR: URL debe empezar con http:// o https://"

    try:
        respuesta = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Agente3573b4n/1.0"
        })
    except requests.exceptions.Timeout:
        return f"ERROR: la URL no respondio en {timeout}s"
    except requests.exceptions.ConnectionError:
        return f"ERROR: no se pudo conectar a '{url}'"
    except requests.exceptions.RequestException as e:
        return f"ERROR al descargar: {e}"

    if respuesta.status_code != 200:
        return f"ERROR: HTTP {respuesta.status_code} ({respuesta.reason})"

    # Tamaño máximo: 100KB para no reventar el contexto del modelo
    limite = 100_000
    texto = respuesta.text[:limite]
    if len(respuesta.text) > limite:
        texto += f"\n[... truncado, {len(respuesta.text) - limite} bytes mas]"

    return texto


def notas(accion: str = "listar", texto: str = "", indice: int = None) -> str:
    import json
    from pathlib import Path

    ruta = Path(__file__).parent / "notas.json"
    if not ruta.exists():
        ruta.write_text("[]", encoding="utf-8")
    datos = json.loads(ruta.read_text(encoding="utf-8"))

    if accion == "listar":
        if not datos:
            return "(no hay notas guardadas)"
        return "\n".join(f"{i+1}. {n}" for i, n in enumerate(datos))

    if accion == "agregar":
        if not texto.strip():
            return "ERROR: texto vacio, no se puede agregar"
        datos.append(texto.strip())
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"OK: nota {len(datos)} agregada"

    if accion == "borrar":
        if not datos:
            return "ERROR: no hay notas para borrar"
        if indice is None:
            return "ERROR: falta indice para borrar"
        if indice < 1 or indice > len(datos):
            return f"ERROR: indice {indice} fuera de rango (1-{len(datos)})"
        borrada = datos.pop(indice - 1)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"OK: nota {indice} borrada ('{borrada}')"

    return f"ERROR: accion desconocida '{accion}'. Usa: listar, agregar, borrar"


def clima(ciudad: str) -> str:
    import requests

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return (
            "ERROR: falta la variable OPENWEATHER_API_KEY.\n"
            "  Consigue una clave gratis en https://openweathermap.org/api\n"
            "  Luego: $env:OPENWEATHER_API_KEY = 'tu-clave'"
        )

    try:
        respuesta = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": ciudad, "appid": api_key, "units": "metric", "lang": "es"},
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        return f"ERROR al consultar el clima: {e}"

    if respuesta.status_code == 404:
        return f"ERROR: ciudad '{ciudad}' no encontrada"
    if respuesta.status_code == 401:
        return "ERROR: API key invalida. Revisa tu OPENWEATHER_API_KEY"
    if respuesta.status_code != 200:
        return f"ERROR: API respondio con HTTP {respuesta.status_code}"

    datos = respuesta.json()
    main = datos["main"]
    viento = datos.get("wind", {})
    clima_str = datos["weather"][0]["description"]

    return (
        f"Ciudad: {datos['name']}, {datos.get('sys', {}).get('country', '')}\n"
        f"Clima: {clima_str}\n"
        f"Temperatura: {main['temp']}°C (sensacion: {main['feels_like']}°C)\n"
        f"Min/Max: {main['temp_min']}°C / {main['temp_max']}°C\n"
        f"Humedad: {main['humidity']}%\n"
        f"Viento: {viento.get('speed', 'N/A')} m/s"
    )


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
    "fecha_hora": fecha_hora,
    "tree": tree,
    "descargar_url": descargar_url,
    "notas": notas,
    "clima": clima,
}
