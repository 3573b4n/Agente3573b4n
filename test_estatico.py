"""
test_estatico.py - Verificacion estatica del agente (Nivel 1)
=============================================================

Ejecuta:
    python test_estatico.py

No necesita API key. Solo verifica que el codigo compile y los imports funcionen.
"""

import os
import sys
import importlib.util

def test_sintaxis_agente():
    """1.1a: agente.py compila sin errores de sintaxis."""
    try:
        with open("agente.py", encoding="utf-8") as f:
            source = f.read()
        compile(source, "agente.py", "exec")
        print("  [OK] agente.py: sintaxis correcta")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] agente.py: {e}")
        return False

def test_sintaxis_llm():
    """1.1b: llm.py compila sin errores de sintaxis."""
    try:
        with open("llm.py", encoding="utf-8") as f:
            source = f.read()
        compile(source, "llm.py", "exec")
        print("  [OK] llm.py: sintaxis correcta")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] llm.py: {e}")
        return False

def test_import_llm():
    """1.2a: llm.py se puede importar (verifica que las dependencias existen)."""
    try:
        import llm
        print("  [OK] import llm: correcto")
        return True
    except ImportError as e:
        print(f"  [FAIL] import llm: {e}")
        return False

def test_import_agente():
    """1.2b: agente.py se puede importar.
    NOTA: agente.py inicializa el modelo al cargarse, necesita API key.
    Por eso seteamos una dummy antes de importar.
    """
    import os
    os.environ["GEMINI_API_KEY"] = "test-key-dummy"
    try:
        import importlib
        # Forzar recarga limpia
        if "agente" in sys.modules:
            del sys.modules["agente"]
        import agente
        print("  [OK] import agente: correcto")
        return True
    except ImportError as e:
        print(f"  [FAIL] import agente: {e}")
        return False
    finally:
        # Limpiar para no contaminar otros tests
        os.environ.pop("GEMINI_API_KEY", None)

def test_tools_existen():
    """1.3: Las 5 tools existen en TOOL_FUNCTIONS y TOOLS_SCHEMA."""
    try:
        import agente
        tools_esperadas = [
            "leer_archivo",
            "listar_directorio",
            "escribir_archivo",
            "correr_comando",
            "buscar_texto",
        ]
        # Verificar TOOL_FUNCTIONS
        for t in tools_esperadas:
            assert t in agente.TOOL_FUNCTIONS, f"TOOL_FUNCTIONS: falta '{t}'"
        print("  [OK] TOOL_FUNCTIONS: las 5 tools existen")

        # Verificar TOOLS_SCHEMA (names)
        nombres_en_schema = set()
        for schema in agente.TOOLS_SCHEMA:
            for decl in schema.get("function_declarations", []):
                nombres_en_schema.add(decl["name"])
        for t in tools_esperadas:
            assert t in nombres_en_schema, f"TOOLS_SCHEMA: falta '{t}'"
        print("  [OK] TOOLS_SCHEMA: las 5 tools declaradas")
        return True
    except AssertionError as e:
        print(f"  [FAIL] tools: {e}")
        return False
    except ImportError as e:
        print(f"  [FAIL] tools: no se pudo importar agente: {e}")
        return False


def test_readme_vs_modulos():
    """1.4: Los módulos listados en el README coinciden con los .py del directorio."""
    import re
    modulos_reales = set()
    for f in os.listdir("."):
        if not f.endswith(".py") or f.startswith("test_"):
            continue
        nombre = f.removesuffix(".py")
        if nombre.isidentifier():
            modulos_reales.add(nombre)

    try:
        with open("README.md", encoding="utf-8") as f:
            readme = f.read()
    except FileNotFoundError:
        print("  [FAIL] README.md no encontrado")
        return False

    # Extraer nombres de módulo de la tabla bajo "## Archivos que lo componen"
    en_seccion = False
    modulos_readme = set()
    for linea in readme.splitlines():
        if linea.startswith("## Archivos que lo componen"):
            en_seccion = True
            continue
        if en_seccion:
            if linea.startswith("## "):
                break
            m = re.match(r"^\| `(\w+)\.py` \|", linea)
            if m:
                modulos_readme.add(m.group(1))

    if not modulos_readme:
        print("  [FAIL] No se encontró la tabla de módulos en el README")
        return False

    solo_en_readme = modulos_readme - modulos_reales
    solo_en_disco = modulos_reales - modulos_readme

    if solo_en_readme:
        print(f"  [FAIL] README menciona módulos que no existen: {solo_en_readme}")
        return False
    if solo_en_disco:
        print(f"  [FAIL] README no menciona módulos que existen: {solo_en_disco}")
        return False

    print(f"  [OK] README y disco coinciden: {len(modulos_reales)} módulos")
    return True


def main():
    print("=" * 50)
    print("  Test estatico del agente (Nivel 1)")
    print("=" * 50)
    print()

    tests = [
        ("Sintaxis agente.py", test_sintaxis_agente),
        ("Sintaxis llm.py", test_sintaxis_llm),
        ("Import llm", test_import_llm),
        ("Import agente", test_import_agente),
        ("Tools existen", test_tools_existen),
        ("README vs modulos", test_readme_vs_modulos),
    ]

    exit_code = 0
    for nombre, fn in tests:
        print(f"[{nombre}]")
        ok = fn()
        if not ok:
            exit_code = 1
        print()

    if exit_code == 0:
        print("TODO OK")
    else:
        print("HUBO FALLOS")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()