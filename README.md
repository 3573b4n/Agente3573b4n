# Agente 3573b4n

**[🇬🇧 English](#-english-summary) · [🇪🇸 Español](#descripción-del-proyecto)**

## 🇬🇧 English summary

Conversational agent in Python powered by **Google Gemini 2.5 Flash**. It runs a continuous reasoning loop: the model decides whether to answer directly or call one of **25 built-in tools** (file operations, directory management, regex search, OS commands restricted by a security whitelist, personal notes, weather, date/time, URL download, tree view, Python execution, system info, Git operations), executes them and reasons over the results until it produces a final answer. State (key-value memories with context support + conversation history) persists to JSON. Provider access is abstracted in `llm.py`, so the LLM backend can be swapped without touching the rest of the code. Ships with **45 tests** that run without an API key. Includes streaming responses, automatic retry with exponential backoff, auto-generated tool schemas from docstrings, HTTP web interface, and detailed logging with rotation.

- **Stack:** Python · Gemini API (function calling) · JSON persistence · dotenv
- **Run:** `pip install -r requirements.txt`, copy `.env.example` to `.env`, then `python agente.py`
- **Web:** `python web_server.py` (opens http://localhost:8080)
- **Tests:** `python test_estatico.py` · `python test_tools.py`

Full documentation in Spanish below.

---

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
| `agente.py` | Entry point ~160 líneas. API key (desde .env), historial de comandos (readline/pyreadline3), inicialización del modelo, loop principal, ejecutor de tools. |
| `config.py` | Logger global con rotación (5MB max, 3 backups), system prompt estructurado, rutas de archivos de persistencia, whitelist/blacklist de seguridad. |
| `memory.py` | Persistencia de recuerdos clave-valor con soporte por contexto (`default`, `proyecto-x`, etc.), búsqueda semántica simple, tags opcionales e historial de conversación. |
| `tools.py` | Implementación de las 25 herramientas + whitelist/blacklist de seguridad + `TOOL_FUNCTIONS`. Incluye herramientas de Git (status, diff, commit, log, branch, stash). |
| `notas.py` | Clase `Notas`: CRUD de notas personales con persistencia en `notas.json`. Primer ejemplo de OOP del proyecto. |
| `schema.py` | Generador automático del schema Gemini a partir de docstrings de `tools.py`. No hay que mantenerlo manualmente. |
| `llm.py` | Wrapper para abstraer el proveedor de LLM (actualmente Gemini). Incluye reintentos con exponential backoff. Permite cambiar de modelo sin tocar el resto. |
| `web_server.py` | Interfaz HTTP ligera con servidor integrado. Endpoint `/chat` para API y página HTML interactiva en `/`. |

## Instalación

### Requisitos

- Python 3.10+
- Una API Key de Google Gemini

### Pasos de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Agente3573b4n
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

   O usando pyproject.toml:
   ```bash
   pip install .
   ```

3. **Configurar las API Keys:**
   Crea un archivo `.env` a partir del ejemplo y rellena tus claves:
   ```bash
   cp .env.example .env
   ```

   Edita `.env` y reemplaza las keys:
   ```ini
   GEMINI_API_KEY=tu-api-key-aqui
   OPENWEATHER_API_KEY=tu-api-key-aqui
   ```

   (Opcional) Tambien funciona con variables de entorno del sistema:

   - **En PowerShell (Windows):**
     ```powershell
     $env:GEMINI_API_KEY = "TU_API_KEY_AQUI"
     ```

   - **En CMD (Windows):**
     ```cmd
     set GEMINI_API_KEY=TU_API_KEY_AQUI
     ```

   - **En Bash/Zsh (Linux/macOS):**
     ```bash
     export GEMINI_API_KEY="TU_API_KEY_AQUI"
     ```

## Herramientas (Tools) Disponibles

El agente tiene acceso a las siguientes herramientas para interactuar con el entorno:

### Archivos y directorios

1. **`leer_archivo(ruta)`**: Lee el contenido de un archivo de texto del disco.
2. **`listar_directorio(ruta=".")`**: Lista archivos y carpetas de un directorio.
3. **`escribir_archivo(ruta, contenido)`**: Crea o sobrescribe un archivo de texto.
4. **`copiar_archivo(origen, destino)`**: Copia un archivo de origen a destino.
5. **`mover_archivo(origen, destino)`**: Mueve o renombra un archivo.
6. **`eliminar_archivo(ruta)`**: Elimina un archivo del disco.
7. **`tree(ruta=".", max_nivel=7)`**: Muestra el árbol de directorios con conectores gráficos.
8. **`descargar_url(url, timeout=15)`**: Descarga el contenido de una URL (máximo 100KB).

### Ejecución y búsqueda

9. **`correr_comando(comando, timeout=30)`**: Ejecuta comandos del sistema operativo de forma segura (whitelist activa).
10. **`ejecutar_python(codigo)`**: Ejecuta código Python directamente y devuelve la salida.
11. **`buscar_texto(pattern, ruta=".", extension=None)`**: Busca un patrón (regex) en archivos.

### Memoria y notas

12. **`recordar(clave, valor)`**: Guarda un recuerdo persistente entre sesiones.
13. **`recuperar(clave)`**: Recupera un recuerdo guardado por su clave.
14. **`listar_recuerdos()`**: Lista todos los recuerdos guardados.
15. **`notas(accion, texto="", indice=None)`**: Gestiona notas personales (listar/agregar/borrar).

### Utilidades

16. **`fecha_hora(zona="Europe/Madrid")`**: Devuelve la fecha y hora actual.
17. **`clima(ciudad)`**: Consulta el clima actual vía OpenWeatherMap.
18. **`ver_logs(lineas=20)`**: Lee las últimas líneas del archivo de log.
19. **`info_sistema()`**: Devuelve información del sistema (SO, Python, espacio en disco).

### Git

20. **`git_status(ruta=".")`**: Muestra el estado de git (archivos modificados, staged, untracked).
21. **`git_diff(ruta=".", archivo=None)`**: Muestra las diferencias sin staged.
22. **`git_commit(mensaje, archivo=None)`**: Hace un commit de los cambios.
23. **`git_log(max_commits=20, ruta=".")`**: Muestra el historial de commits recientes.
24. **`git_branch(ruta=".")`**: Muestra las ramas del repositorio y la rama actual.
25. **`git_stash(accion, mensaje)`**: Stash/pop de cambios temporales (save/pop/list/drop).

## Interfaz Web

El agente incluye una interfaz HTTP ligera para usarlo desde un navegador:

```bash
python web_server.py          # Puerto 8080 (por defecto)
python web_server.py 9000     # Puerto personalizado
```

- **Interfaz visual:** Abre http://localhost:8080 en tu navegador
- **API REST:** `POST /chat` con body `{"prompt": "tu mensaje"}` → `{"response": "respuesta"}`
- **Health check:** `GET /health` → `{"status": "ok"}`

## Tests

Dos suites de tests, sin necesidad de API key (se setea una dummy automáticamente):

```bash
# Test estático — verifica sintaxis, imports, tools existen
python test_estatico.py

# Test unitarios — verifica comportamiento de cada tool
python test_tools.py

# Ambos: 45+ tests en total
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

## Características Avanzadas

### Historial de Comandos
Usa las flechas ↑↓ para navegar por el historial de comandos de la sesión. El historial se guarda en `.agente_history` y persiste entre sesiones.

### Logging Detallado
Los logs se guardan en `agente.log` con formato detallado: `hora [nivel] modulo - funcion:linea — mensaje`. Rotación automática a 5MB con 3 archivos de backup.

### Memoria por Contexto
Los recuerdos pueden organizarse por contexto (`default`, `proyecto-x`, etc.) y buscar por término. Usa `recordar("clave", "valor", contexto="proyecto-x")` para guardar en un contexto específico.

### Streaming
Las respuestas se muestran en tiempo real mientras se generan, no esperas a tener la respuesta completa.

### Reintentos Automáticos
Ante fallos de API (rate limit, errores 5xx), el agente reintenta automáticamente con exponential backoff (hasta 3 intentos).
