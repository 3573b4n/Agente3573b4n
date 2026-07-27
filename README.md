# Agente 3573b4n

## Descripción del Proyecto
Agente conversacional en Python, potenciado por Google Gemini 2.5 Flash. Puede interactuar con el usuario, decidir cuándo usar herramientas para actuar sobre el sistema de archivos y el sistema operativo, ejecutarlas y razonar con los resultados.

El agente opera en un bucle continuo:
1. El usuario proporciona una entrada.
2. El modelo (Gemini) decide si necesita usar una herramienta o si puede responder directamente.
3. Si el modelo solicita una herramienta, el agente la ejecuta y el resultado se devuelve al modelo.
4. El modelo razona con el nuevo resultado y decide el siguiente paso (otra herramienta o una respuesta al usuario).
5. Este ciclo se repite hasta que el modelo decide responder al usuario.

## Archivos que lo componen

| Módulo | Responsabilidad |
|---|---|
| `agente.py` | Entry point ~120 líneas. API key, inicialización del modelo, loop principal, ejecutor de tools. Re-exporta símbolos para tests. |
| `config.py` | Logger global, system prompt (`SISTEMA`), rutas de archivos de persistencia. |
| `memory.py` | Persistencia de recuerdos clave-valor (`memoria.json`) e historial de conversación (`historial.json`). |
| `tools.py` | Implementación de las 9 herramientas + whitelist/blacklist de seguridad + `TOOL_FUNCTIONS`. |
| `schema.py` | `TOOLS_SCHEMA` con las declaraciones en formato `function_declarations` que consume la API de Gemini. |
| `llm.py` | Wrapper para abstraer el proveedor de LLM (actualmente Gemini). Permite cambiar de modelo sin tocar el resto. |

## Instalación

### Requisitos
- Python 3.x
- Una API Key de Google Gemini.

### Pasos de Instalación

1.  **Clonar el repositorio** (si aplica, asumiendo que el usuario tiene el proyecto localmente).
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd mi-agente
    ```

2.  **Instalar dependencias de Python**:
    ```bash
    pip install google-generativeai
    ```

3.  **Configurar la API Key**:
    Es **crucial** configurar tu API Key de Google Gemini como una variable de entorno. Esto asegura que tu clave no esté hardcodeada en el código.

    -   **En PowerShell (Windows):**
        ```powershell
        $env:GEMINI_API_KEY = "TU_API_KEY_AQUI"
        # O $env:GOOGLE_API_KEY = "TU_API_KEY_AQUI"
        ```

    -   **En CMD (Windows):**
        ```cmd
        set GEMINI_API_KEY=TU_API_KEY_AQUI
        # O set GOOGLE_API_KEY=TU_API_KEY_AQUI
        ```

    -   **En Bash/Zsh (Linux/macOS):**
        ```bash
        export GEMINI_API_KEY="TU_API_KEY_AQUI"
        # O export GOOGLE_API_KEY="TU_API_KEY_AQUI"
        ```

    Reemplaza `"TU_API_KEY_AQUI"` con tu clave real obtenida de Google AI Studio.

## Herramientas (Tools) Disponibles

El agente tiene acceso a las siguientes herramientas para interactuar con el entorno:

1.  **`leer_archivo(ruta)`**: Lee el contenido de un archivo de texto del disco.
    -   **Parámetros**: `ruta` (string) - Ruta del archivo a leer (ej: `'main.py'`).
    -   **Ejemplo de uso interno**: `leer_archivo('src/utils.py')`

2.  **`listar_directorio(ruta='.')`**: Lista los archivos y carpetas de un directorio.
    -   **Parámetros**: `ruta` (string, opcional) - Ruta del directorio a listar (Default: `'.'`).
    -   **Ejemplo de uso interno**: `listar_directorio('documentos/')`

3.  **`escribir_archivo(ruta, contenido)`**: Crea o sobrescribe un archivo de texto con el contenido dado.
    -   **Parámetros**: `ruta` (string) - Ruta del archivo a escribir. `contenido` (string) - El texto completo a escribir.
    -   **Ejemplo de uso interno**: `escribir_archivo('notas.txt', 'Esto es una nota.')`

4.  **`correr_comando(comando, timeout=30)`**: Ejecuta comandos del sistema operativo de forma segura. Solo permite comandos de una whitelist predefinida.
    -   **Parámetros**: `comando` (string) - El comando completo a ejecutar (ej: `'python script.py'` ). `timeout` (integer, opcional) - Segundos máximos de espera (Default: `30`).
    -   **Whitelist de comandos**: `python`, `pip`, `dir`, `ls`, `type`, `cat`, `echo`, `mkdir`, `git status`, `git log`, `git diff`, `git branch`, `git show`, `git ls-files`.
    -   **Ejemplo de uso interno**: `correr_comando('dir C:\\Users')`

5.  **`buscar_texto(pattern, ruta='.', extension=None)`**: Busca un patrón (regex) en archivos de texto.
    -   **Parámetros**: `pattern` (string) - Expresión regular a buscar (ej: `'def\\s+\\w+'`). `ruta` (string, opcional) - Directorio base a buscar (Default: `'.'`). `extension` (string, opcional) - Filtro por extensión (ej: `'*.py'` ).
    -   **Resultado**: Devuelve coincidencias en formato `archivo:linea:contenido`.
    -   **Ejemplo de uso interno**: `buscar_texto('TODO', extension='*.py')`

## Tests

Dos suites de tests, sin necesidad de API key (se setea una dummy automáticamente):

```bash
# Test estático — verifica sintaxis, imports, tools existen
python test_estatico.py

# Test unitarios — verifica comportamiento de cada tool
python test_tools.py

# Ambos: 17 tests en total (5 + 12)
```

## Ejemplo de Uso

Para iniciar una conversación con el agente, ejecuta el script principal:

```bash
python agente.py
```

Luego, podrás interactuar con el agente en la terminal. Aquí tienes un ejemplo de una posible interacción:

```
ahora te toca a ti > listame los archivos en el directorio actual
  [tool] listar_directorio({})
  [resultado] agente.py
llm.py
README.md
test2.txt

tú > Aquí tienes los archivos en el directorio actual:
- agente.py
- llm.py
- README.md
- test2.txt

ahora te toca a ti > cual es el contenido de test2.txt?
  [tool] leer_archivo({'ruta': 'test2.txt'})
  [resultado] segundo test
tú > El contenido de test2.txt es: "segundo test".

ahora te toca a ti > creame un archivo llamado mi_nuevo_archivo.txt con el texto "Hola, soy un archivo nuevo."
  [tool] escribir_archivo({'ruta': 'mi_nuevo_archivo.txt', 'contenido': 'Hola, soy un archivo nuevo.'})
  [resultado] OK: archivo 'mi_nuevo_archivo.txt' escrito (27 caracteres)
tú > He creado el archivo mi_nuevo_archivo.txt con el contenido "Hola, soy un archivo nuevo."
```