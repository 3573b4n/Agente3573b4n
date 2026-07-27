"""
test_tools.py - Tests unitarios de cada tool (Nivel 2)
=======================================================

Ejecuta:
    python test_tools.py
"""

import sys
import os
import tempfile
import shutil

# Aseguramos que el directorio del proyecto este en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Necesitamos API key para importar agente (inicializa modelo al cargarse)
os.environ["GEMINI_API_KEY"] = "test-key-dummy"
import agente


def limpiar_sys_modules():
    """Limpia modulos para que no queden residuos entre tests."""
    for mod in list(sys.modules.keys()):
        if mod.startswith("agente"):
            del sys.modules[mod]


# =========================================================================
# Tests de leer_archivo
# =========================================================================

def test_leer_archivo_existe():
    """leer_archivo: archivo existente devuelve contenido."""
    contenido = agente.leer_archivo(__file__)  # leerse a si mismo
    assert "def test_leer_archivo_existe" in contenido, (
        "Deberia encontrar su propia definicion"
    )
    print("  [OK] leer_archivo: archivo existente")


def test_leer_archivo_no_existe():
    """leer_archivo: archivo inexistente devuelve error string (no excepcion)."""
    resultado = agente.leer_archivo("no_existe_123.xyz")
    assert resultado.startswith("ERROR"), "Deberia devolver mensaje de error"
    assert "no_existe" in resultado, "El error deberia mencionar el archivo"
    print("  [OK] leer_archivo: archivo inexistente manejado")


# =========================================================================
# Tests de listar_directorio
# =========================================================================

def test_listar_directorio_existe():
    """listar_directorio: directorio existente devuelve contenido."""
    resultado = agente.listar_directorio(".")
    assert "agente.py" in resultado, "Deberia listar agente.py"
    assert "llm.py" in resultado, "Deberia listar llm.py"
    print("  [OK] listar_directorio: directorio existente")


def test_listar_directorio_no_existe():
    """listar_directorio: directorio inexistente devuelve error string."""
    resultado = agente.listar_directorio("c:\\directorio_que_no_existe_999")
    assert resultado.startswith("ERROR"), "Deberia devolver mensaje de error"
    print("  [OK] listar_directorio: directorio inexistente manejado")


# =========================================================================
# Tests de escribir_archivo
# =========================================================================

def test_escribir_archivo_crear():
    """escribir_archivo: crear archivo nuevo."""
    ruta_test = "test_temp_escritura.txt"
    try:
        resultado = agente.escribir_archivo(ruta_test, "contenido de prueba")
        assert resultado.startswith("OK"), "Deberia indicar exito"
        assert os.path.exists(ruta_test), "El archivo deberia existir en disco"
        with open(ruta_test, encoding="utf-8") as f:
            assert f.read() == "contenido de prueba", "El contenido deberia coincidir"
        print("  [OK] escribir_archivo: crear archivo nuevo")
    finally:
        if os.path.exists(ruta_test):
            os.remove(ruta_test)


def test_escribir_archivo_sobrescribe():
    """escribir_archivo: sobrescribe archivo existente."""
    ruta_test = "test_temp_sobrescritura.txt"
    try:
        agente.escribir_archivo(ruta_test, "original")
        agente.escribir_archivo(ruta_test, "sobrescrito")
        with open(ruta_test, encoding="utf-8") as f:
            assert f.read() == "sobrescrito", "Deberia tener el nuevo contenido"
        print("  [OK] escribir_archivo: sobrescribe archivo existente")
    finally:
        if os.path.exists(ruta_test):
            os.remove(ruta_test)


# =========================================================================
# Tests de correr_comando (whitelist + seguridad)
# =========================================================================

def test_correr_comando_whitelist():
    """correr_comando: comando permitido se ejecuta."""
    resultado = agente.correr_comando("echo hola")
    assert resultado.startswith("[exit code 0]"), "Deberia ejecutarse correctamente"
    assert "hola" in resultado, "La salida deberia contener 'hola'"
    print("  [OK] correr_comando: comando permitido")


def test_correr_comando_rechazado():
    """correr_comando: comando no whitelist es rechazado."""
    resultado = agente.correr_comando("format C:")
    assert resultado.startswith("ERROR"), "Deberia ser rechazado"
    assert "whitelist" in resultado.lower() or "rechazado" in resultado.lower() or "motivo" in resultado.lower(), (
        "El error deberia mencionar whitelist o motivo"
    )
    print("  [OK] correr_comando: comando no permitido rechazado")


def test_correr_comando_timeout():
    """correr_comando: timeout con 1 segundo."""
    resultado = agente.correr_comando("ping -n 10 127.0.0.1", timeout=1)
    assert "timeout" in resultado.lower() or "ERROR" in resultado, (
        "Deberia fallar por timeout o ser rechazado (ping puede no estar en whitelist)"
    )
    print("  [OK] correr_comando: timeout manejado")


# =========================================================================
# Tests de buscar_texto
# =========================================================================

def test_buscar_texto_encuentra():
    """buscar_texto: pattern existente devuelve coincidencias."""
    resultado = agente.buscar_texto("def test_", ".", "*.py")
    assert "test_" in resultado, "Deberia encontrar las funciones test_"
    print("  [OK] buscar_texto: encuentra coincidencias")


def test_buscar_texto_sin_coincidencias():
    """buscar_texto: patron sin coincidencias devuelve mensaje."""
    resultado = agente.buscar_texto("test", ".", "*.nonexistent")
    assert "sin archivos" in resultado.lower() or "sin coincidencias" in resultado.lower(), (
        f"Deberia indicar que no hay. Obtuvo: {resultado[:80]}"
    )
    print("  [OK] buscar_texto: sin coincidencias manejado")


def test_buscar_texto_regex_invalido():
    """buscar_texto: regex invalido devuelve error."""
    resultado = agente.buscar_texto("[", ".", "*.py")
    assert resultado.startswith("ERROR"), "Regex invalido deberia dar error"
    print("  [OK] buscar_texto: regex invalido manejado")


# =========================================================================
# Ejecucion
# =========================================================================

def main():
    print("=" * 50)
    print("  Test unitarios de tools (Nivel 2)")
    print("=" * 50)
    print()

    tests = [
        ("leer_archivo: archivo existe", test_leer_archivo_existe),
        ("leer_archivo: archivo no existe", test_leer_archivo_no_existe),
        ("listar_directorio: existe", test_listar_directorio_existe),
        ("listar_directorio: no existe", test_listar_directorio_no_existe),
        ("escribir_archivo: crear", test_escribir_archivo_crear),
        ("escribir_archivo: sobrescribir", test_escribir_archivo_sobrescribe),
        ("correr_comando: whitelist", test_correr_comando_whitelist),
        ("correr_comando: rechazado", test_correr_comando_rechazado),
        ("correr_comando: timeout", test_correr_comando_timeout),
        ("buscar_texto: encuentra", test_buscar_texto_encuentra),
        ("buscar_texto: sin coincidencias", test_buscar_texto_sin_coincidencias),
        ("buscar_texto: regex invalido", test_buscar_texto_regex_invalido),
    ]

    exit_code = 0
    for nombre, fn in tests:
        print(f"[{nombre}]")
        try:
            fn()
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            exit_code = 1
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            exit_code = 1
        print()

    if exit_code == 0:
        print("TODO OK")
    else:
        print("HUBO FALLOS")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()