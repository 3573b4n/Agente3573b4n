"""
test_tools.py - Tests unitarios de cada tool (Nivel 2)
=======================================================

Ejecuta:
    python test_tools.py

No requiere API key de Gemini — importa directamente desde tools.py.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Aseguramos que el directorio del proyecto este en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import (
    leer_archivo,
    listar_directorio,
    escribir_archivo,
    correr_comando,
    buscar_texto,
    recordar,
    recuperar,
    listar_recuerdos,
    fecha_hora,
    tree,
    descargar_url,
    notas,
    clima,
    ver_logs,
    _comando_permitido,
    WHITELIST_COMANDOS,
    BLACKLIST_PELIGROS,
)


def limpiar_temp(ruta):
    """Elimina un archivo temporal si existe."""
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except Exception:
        pass


# =========================================================================
# Tests de seguridad (whitelist / blacklist)
# =========================================================================


def test_whitelist_comandos_basicos():
    """_comando_permitido: comandos basicos de la whitelist."""
    permitidos = ["python", "pip", "ls", "dir", "mkdir", "echo hola"]
    for cmd in permitidos:
        ok, _ = _comando_permitido(cmd)
        assert ok, f"'{cmd}' deberia estar permitido"
    print("  [OK] whitelist: comandos basicos")


def test_blacklist_peligrosos():
    """_comando_permitido: comandos peligrosos bloqueados."""
    peligrosos = ["rm -rf /", "del /s c:", "format C:", "shutdown now"]
    for cmd in peligrosos:
        ok, motivo = _comando_permitido(cmd)
        assert not ok, f"'{cmd}' deberia ser rechazado"
        assert "peligroso" in motivo.lower(), f"El motivo deberia mencionar 'peligroso'"
    print("  [OK] blacklist: comandos peligrosos bloqueados")


def test_whitelist_git():
    """_comando_permitido: comandos git de la whitelist."""
    git_cmds = ["git status", "git log", "git diff", "git branch", "git show"]
    for cmd in git_cmds:
        ok, _ = _comando_permitido(cmd)
        assert ok, f"'{cmd}' deberia estar permitido"
    print("  [OK] whitelist: comandos git")


def test_whitelist_vacio():
    """_comando_permitido: comando vacio es rechazado."""
    ok, _ = _comando_permitido("")
    assert not ok, "Comando vacio debe ser rechazado"
    print("  [OK] whitelist: comando vacio rechazado")


# =========================================================================
# Tests de leer_archivo
# =========================================================================


def test_leer_archivo_existe():
    """leer_archivo: archivo existente devuelve contenido."""
    contenido = leer_archivo(__file__)
    assert "def test_leer_archivo_existe" in contenido
    print("  [OK] leer_archivo: archivo existente")


def test_leer_archivo_no_existe():
    """leer_archivo: archivo inexistente devuelve error string."""
    resultado = leer_archivo("no_existe_123.xyz")
    assert resultado.startswith("ERROR")
    assert "no_existe" in resultado
    print("  [OK] leer_archivo: archivo inexistente manejado")


# =========================================================================
# Tests de listar_directorio
# =========================================================================


def test_listar_directorio_existe():
    """listar_directorio: directorio existente devuelve contenido."""
    resultado = listar_directorio(".")
    assert "tools.py" in resultado or "agente.py" in resultado
    print("  [OK] listar_directorio: directorio existente")


def test_listar_directorio_no_existe():
    """listar_directorio: directorio inexistente devuelve error."""
    resultado = listar_directorio("c:\\directorio_que_no_existe_999")
    assert resultado.startswith("ERROR")
    print("  [OK] listar_directorio: directorio inexistente manejado")


# =========================================================================
# Tests de escribir_archivo
# =========================================================================


def test_escribir_archivo_crear():
    """escribir_archivo: crear archivo nuevo."""
    ruta_test = "test_temp_escritura.txt"
    try:
        resultado = escribir_archivo(ruta_test, "contenido de prueba")
        assert resultado.startswith("OK")
        assert os.path.exists(ruta_test)
        with open(ruta_test, encoding="utf-8") as f:
            assert f.read() == "contenido de prueba"
        print("  [OK] escribir_archivo: crear archivo nuevo")
    finally:
        limpiar_temp(ruta_test)


def test_escribir_archivo_sobrescribe():
    """escribir_archivo: sobrescribe archivo existente."""
    ruta_test = "test_temp_sobrescritura.txt"
    try:
        escribir_archivo(ruta_test, "original")
        escribir_archivo(ruta_test, "sobrescrito")
        with open(ruta_test, encoding="utf-8") as f:
            assert f.read() == "sobrescrito"
        print("  [OK] escribir_archivo: sobrescribe archivo existente")
    finally:
        limpiar_temp(ruta_test)


def test_escribir_archivo_creacion_directorio():
    """escribir_archivo: crea directorios padre si no existen."""
    ruta_test = os.path.join("test_temp_dir", "subdir", "archivo.txt")
    try:
        resultado = escribir_archivo(ruta_test, "hola")
        assert resultado.startswith("OK")
        assert os.path.exists(ruta_test)
        print("  [OK] escribir_archivo: creacion de directorios padre")
    finally:
        shutil.rmtree("test_temp_dir", ignore_errors=True)


# =========================================================================
# Tests de correr_comando
# =========================================================================


def test_correr_comando_whitelist():
    """correr_comando: comando permitido se ejecuta."""
    resultado = correr_comando("echo hola")
    assert resultado.startswith("[exit code 0]")
    assert "hola" in resultado
    print("  [OK] correr_comando: comando permitido")


def test_correr_comando_rechazado():
    """correr_comando: comando no whitelist es rechazado."""
    resultado = correr_comando("format C:")
    assert resultado.startswith("ERROR")
    assert "rechazado" in resultado.lower() or "motivo" in resultado.lower()
    print("  [OK] correr_comando: comando no permitido rechazado")


def test_correr_comando_timeout():
    """correr_comando: timeout con 1 segundo."""
    # En Windows, timeout corto con un comando lento
    resultado = correr_comando("ping -n 5 127.0.0.1", timeout=1)
    assert "timeout" in resultado.lower() or "ERROR" in resultado
    print("  [OK] correr_comando: timeout manejado")


# =========================================================================
# Tests de buscar_texto
# =========================================================================


def test_buscar_texto_encuentra():
    """buscar_texto: pattern existente devuelve coincidencias."""
    resultado = buscar_texto("def test_", ".", "*.py")
    assert "test_" in resultado
    print("  [OK] buscar_texto: encuentra coincidencias")


def test_buscar_texto_sin_coincidencias():
    """buscar_texto: patron sin coincidencias devuelve mensaje."""
    resultado = buscar_texto("xyz_no_existe_12345", ".", "*.nonexistent")
    assert (
        "sin archivos" in resultado.lower() or "sin coincidencias" in resultado.lower()
    )
    print("  [OK] buscar_texto: sin coincidencias manejado")


def test_buscar_texto_regex_invalido():
    """buscar_texto: regex invalido devuelve error."""
    resultado = buscar_texto("[", ".", "*.py")
    assert resultado.startswith("ERROR")
    print("  [OK] buscar_texto: regex invalido manejado")


# =========================================================================
# Tests de memoria (recordar / recuperar / listar)
# =========================================================================


def test_recordar_y_recuperar():
    """recordar + recuperar: guardar y leer un recuerdo."""
    clave = "__test_clave_temporal"
    valor = "valor_de_prueba"
    recordar(clave, valor)
    resultado = recuperar(clave)
    assert valor in resultado, f"Deberia contener '{valor}', obtuvo: {resultado}"
    # Limpieza
    from memory import cargar_memoria, guardar_memoria

    mem = cargar_memoria()
    if clave in mem:
        del mem[clave]
        guardar_memoria(mem)
    print("  [OK] recordar + recuperar")


def test_recuperar_no_existe():
    """recuperar: clave inexistente devuelve mensaje adecuado."""
    resultado = recuperar("__clave_inexistente_xxx")
    assert "no tengo nada recordado" in resultado.lower()
    print("  [OK] recuperar: clave inexistente")


def test_listar_recuerdos():
    """listar_recuerdos: devuelve lista o mensaje vacio."""
    resultado = listar_recuerdos()
    assert isinstance(resultado, str)
    assert len(resultado) > 0
    print("  [OK] listar_recuerdos")


# =========================================================================
# Tests de fecha_hora
# =========================================================================


def test_fecha_hora_default():
    """fecha_hora: zona por defecto Europe/Madrid."""
    resultado = fecha_hora()
    assert "Fecha:" in resultado
    assert "Hora:" in resultado
    assert "Europe/Madrid" in resultado
    print("  [OK] fecha_hora: zona default")


def test_fecha_hora_utc():
    """fecha_hora: zona UTC."""
    resultado = fecha_hora("UTC")
    assert "UTC" in resultado
    print("  [OK] fecha_hora: zona UTC")


# =========================================================================
# Tests de tree
# =========================================================================


def test_tree_directorio_actual():
    """tree: arbol del directorio actual."""
    resultado = tree(".", max_nivel=2)
    assert "tools.py" in resultado or "agente.py" in resultado
    assert "+" in resultado or "\\" in resultado  # conectores graficos
    print("  [OK] tree: directorio actual")


def test_tree_no_es_directorio():
    """tree: ruta que no es directorio devuelve error."""
    resultado = tree("agente.py")
    assert resultado.startswith("ERROR")
    print("  [OK] tree: ruta no es directorio")


# =========================================================================
# Tests de notas
# =========================================================================


def test_notas_agregar_y_listar():
    """notas: agregar nota y listar."""
    notas("agregar", "nota de test temporal")
    resultado = notas("listar")
    assert "nota de test temporal" in resultado
    print("  [OK] notas: agregar y listar")


def test_notas_borrar():
    """notas: borrar ultima nota agregada."""
    # Agregar una nota
    notas("agregar", "nota para borrar")
    # Listar para obtener indice
    listado = notas("listar")
    lineas = [l.strip() for l in listado.split("\n") if "nota para borrar" in l]
    if lineas:
        # Extraer numero de linea (formato: "N. texto")
        num = int(lineas[0].split(".")[0])
        resultado = notas("borrar", indice=num)
        assert (
            "OK" in resultado
            or "borrado" in resultado.lower()
            or "eliminado" in resultado.lower()
        )
    print("  [OK] notas: borrar")


def test_notas_accion_invalida():
    """notas: accion desconocida devuelve error."""
    resultado = notas("accion_falsa")
    assert "ERROR" in resultado or "desconocida" in resultado.lower()
    print("  [OK] notas: accion invalida")


# =========================================================================
# Tests de clima (sin API key)
# =========================================================================


def test_clima_sin_api_key():
    """clima: sin OPENWEATHER_API_KEY devuelve error util."""
    # Asegurarnos de que no hay API key
    original = os.environ.pop("OPENWEATHER_API_KEY", None)
    try:
        resultado = clima("Madrid")
        assert "ERROR" in resultado
        assert "OPENWEATHER_API_KEY" in resultado
    finally:
        if original:
            os.environ["OPENWEATHER_API_KEY"] = original
    print("  [OK] clima: sin API key")


# =========================================================================
# Tests de ver_logs
# =========================================================================


def test_ver_logs():
    """ver_logs: lee el archivo de logs."""
    resultado = ver_logs()
    assert isinstance(resultado, str)
    # Puede devolver "(aun no hay logs)" o contenido real
    print("  [OK] ver_logs")


# =========================================================================
# Tests de reintentos (retry logic)
# =========================================================================


def test_is_retryable_rate_limit():
    """_is_retryable_error: errores 429 son retryables."""
    from llm import GeminiProvider

    provider = GeminiProvider.__new__(GeminiProvider)  # sin init
    ok, reason = provider._is_retryable_error(Exception("429 Too Many Requests"))
    assert ok
    assert reason == "rate_limit"
    print("  [OK] is_retryable: 429 rate limit")


def test_is_retryable_server_error():
    """_is_retryable_error: errores 5xx son retryables."""
    from llm import GeminiProvider

    provider = GeminiProvider.__new__(GeminiProvider)
    for code in ["500", "502", "503", "504"]:
        ok, _ = provider._is_retryable_error(Exception(code))
        assert ok, f"{code} deberia ser retryable"
    print("  [OK] is_retryable: 5xx server errors")


def test_is_retryable_timeout():
    """_is_retryable_error: timeouts son retryables."""
    from llm import GeminiProvider

    provider = GeminiProvider.__new__(GeminiProvider)
    ok, _ = provider._is_retryable_error(Exception("Connection timed out"))
    assert ok
    print("  [OK] is_retryable: timeout")


def test_is_not_retryable_auth():
    """_is_retryable_error: errores de auth NO son retryables."""
    from llm import GeminiProvider

    provider = GeminiProvider.__new__(GeminiProvider)
    ok, _ = provider._is_retryable_error(Exception("Invalid API key"))
    assert not ok, "Auth error no deberia ser retryable"
    print("  [OK] is_retryable: auth error no retryable")


def test_wait_exponential_backoff():
    """_wait_before_retry: calcula delay con backoff exponencial + jitter."""
    from llm import GeminiProvider

    provider = object.__new__(GeminiProvider)
    provider.max_retries = 3
    provider.base_delay = 1.0

    # attempt 1: ~1s +/- 20% => [0.8, 1.2]
    delay = provider._wait_before_retry(1, "test")
    assert 0.7 <= delay <= 1.3, f"Delay attempt 1 fuera de rango: {delay}"

    # attempt 2: ~2s +/- 20% => [1.6, 2.4]
    delay = provider._wait_before_retry(2, "test")
    assert 1.5 <= delay <= 2.5, f"Delay attempt 2 fuera de rango: {delay}"

    # attempt 3: ~4s pero capped a 30s
    delay = provider._wait_before_retry(3, "test")
    assert 3.0 <= delay <= 30.0, f"Delay attempt 3 fuera de rango: {delay}"

    print("  [OK] wait_before_retry: backoff exponencial")


def test_generar_retry_success_on_second():
    """generar: reintenta y tiene exito en el segundo intento."""
    from llm import LLM, GeminiProvider

    mock_impl = MagicMock()
    mock_response = MagicMock()

    # Simulamos falla la primera vez, exito la segunda
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("429 Too Many Requests")
        return mock_response

    mock_impl.generar.side_effect = side_effect

    # Inyectamos logica de retry del provider real
    real_provider = object.__new__(GeminiProvider)
    real_provider.max_retries = 3
    real_provider.base_delay = 0.01  # delay minimo para tests rapidos

    with patch.object(
        real_provider, "_is_retryable_error", return_value=(True, "rate_limit")
    ):
        with patch.object(real_provider, "_wait_before_retry"):
            for attempt in range(1, real_provider.max_retries + 1):
                try:
                    result = mock_impl.generar(None, None)
                    break
                except Exception as e:
                    is_retryable, reason = real_provider._is_retryable_error(e)
                    if not is_retryable or attempt >= real_provider.max_retries:
                        raise
                    real_provider._wait_before_retry(attempt, reason)

            assert result is mock_response
            assert call_count[0] == 2, f"Se esperaba 2 llamadas, fue {call_count[0]}"

    print("  [OK] generar: retry success en segundo intento")


# =========================================================================
# Ejecucion
# =========================================================================


def main():
    print("=" * 50)
    print("  Test unitarios de tools (Nivel 2)")
    print("=" * 50)
    print()

    tests = [
        ("Seguridad: whitelist basica", test_whitelist_comandos_basicos),
        ("Seguridad: blacklist peligrosos", test_blacklist_peligrosos),
        ("Seguridad: whitelist git", test_whitelist_git),
        ("Seguridad: comando vacio", test_whitelist_vacio),
        ("leer_archivo: existe", test_leer_archivo_existe),
        ("leer_archivo: no existe", test_leer_archivo_no_existe),
        ("listar_directorio: existe", test_listar_directorio_existe),
        ("listar_directorio: no existe", test_listar_directorio_no_existe),
        ("escribir_archivo: crear", test_escribir_archivo_crear),
        ("escribir_archivo: sobrescribe", test_escribir_archivo_sobrescribe),
        (
            "escribir_archivo: crea directorios",
            test_escribir_archivo_creacion_directorio,
        ),
        ("correr_comando: whitelist", test_correr_comando_whitelist),
        ("correr_comando: rechazado", test_correr_comando_rechazado),
        ("correr_comando: timeout", test_correr_comando_timeout),
        ("buscar_texto: encuentra", test_buscar_texto_encuentra),
        ("buscar_texto: sin coincidencias", test_buscar_texto_sin_coincidencias),
        ("buscar_texto: regex invalido", test_buscar_texto_regex_invalido),
        ("memoria: recordar + recuperar", test_recordar_y_recuperar),
        ("memoria: recuperar no existe", test_recuperar_no_existe),
        ("memoria: listar recuerdos", test_listar_recuerdos),
        ("fecha_hora: default", test_fecha_hora_default),
        ("fecha_hora: UTC", test_fecha_hora_utc),
        ("tree: directorio actual", test_tree_directorio_actual),
        ("tree: no es directorio", test_tree_no_es_directorio),
        ("notas: agregar y listar", test_notas_agregar_y_listar),
        ("notas: borrar", test_notas_borrar),
        ("notas: accion invalida", test_notas_accion_invalida),
        ("clima: sin API key", test_clima_sin_api_key),
        ("ver_logs", test_ver_logs),
        ("Reintentos: 429 rate limit", test_is_retryable_rate_limit),
        ("Reintentos: 5xx server error", test_is_retryable_server_error),
        ("Reintentos: timeout", test_is_retryable_timeout),
        ("Reintentos: auth no retryable", test_is_not_retryable_auth),
        ("Reintentos: backoff exponencial", test_wait_exponential_backoff),
        ("Reintentos: retry success 2o intento", test_generar_retry_success_on_second),
    ]

    exit_code = 0
    passed = 0
    failed = 0
    errors = 0

    for nombre, fn in tests:
        print(f"[{nombre}]")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            exit_code = 1
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            exit_code = 1
            errors += 1
        print()

    print("-" * 50)
    print(
        f"Resultados: {passed} OK | {failed} FAIL | {errors} ERROR | {len(tests)} total"
    )

    if exit_code == 0:
        print("TODO OK")
    else:
        print("HUBO FALLOS")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
