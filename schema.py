TOOLS_SCHEMA = [
    {
        "function_declarations": [
            {
                "name": "leer_archivo",
                "description": "Lee el contenido de un archivo de texto.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ruta": {
                            "type": "string",
                            "description": "Ruta del archivo a leer, ej: 'main.py' o 'src/utils.py'."
                        }
                    },
                    "required": ["ruta"]
                }
            },
            {
                "name": "listar_directorio",
                "description": "Lista los archivos y carpetas de un directorio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ruta": {
                            "type": "string",
                            "description": "Ruta del directorio a listar. Default: '.' (directorio actual)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "escribir_archivo",
                "description": "Crea o sobrescribe un archivo de texto. Si el archivo ya existe, su contenido se reemplaza por completo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ruta": {
                            "type": "string",
                            "description": "Ruta del archivo a escribir. Puede ser relativa ('notas.txt') o absoluta ('C:\\Users\\algo\\archivo.py')."
                        },
                        "contenido": {
                            "type": "string",
                            "description": "El texto completo a escribir en el archivo. Reemplaza cualquier contenido previo."
                        }
                    },
                    "required": ["ruta", "contenido"]
                }
            },
            {
                "name": "correr_comando",
                "description": "Ejecuta un comando del sistema operativo de forma segura. Solo permite comandos de una whitelist (python, pip, dir, ls, type, cat, echo, mkdir, git status/log/diff/branch/show/ls-files). El comando corre en el directorio actual de ejecucion.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "comando": {
                            "type": "string",
                            "description": "Comando completo a ejecutar, ej: 'python test.py', 'dir C:\\Users', 'git status', 'echo hola'."
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Segundos maximos de espera. Default: 30. Si el comando tarda mas, se cancela."
                        }
                    },
                    "required": ["comando"]
                }
            },
            {
                "name": "buscar_texto",
                "description": "Busca un pattern (regex) en archivos de texto. Devuelve coincidencias con archivo:linea:contenido. Parametros opcionales: extension para filtrar (ej: '*.py'). Limita a 50 resultados.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex a buscar, ej: 'def\\\\s+\\\\w+', 'TODO', 'import.*requests'."
                        },
                        "ruta": {
                            "type": "string",
                            "description": "Directorio base a buscar. Default: '.' (actual)."
                        },
                        "extension": {
                            "type": "string",
                            "description": "Filtro por extension, ej: '*.py', '*.txt'. Default: todos."
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "recordar",
                "description": "Guarda un recuerdo persistente (clave=valor). El agente recuerda este dato entre sesiones. Usalo cuando el usuario te pida recordar algo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clave": {
                            "type": "string",
                            "description": "Nombre del recuerdo, ej: 'nombre_del_usuario', 'proyecto_favorito'."
                        },
                        "valor": {
                            "type": "string",
                            "description": "Valor a recordar, ej: 'Juan', 'mi-agente'."
                        }
                    },
                    "required": ["clave", "valor"]
                }
            },
            {
                "name": "recuperar",
                "description": "Recupera un recuerdo guardado previamente por su clave. Usalo cuando el usuario te pregunte algo que deberias recordar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clave": {
                            "type": "string",
                            "description": "Clave del recuerdo a recuperar, ej: 'nombre_del_usuario'."
                        }
                    },
                    "required": ["clave"]
                }
            },
            {
                "name": "listar_recuerdos",
                "description": "Lista todos los recuerdos guardados. Usalo para mostrar al usuario todo lo que el agente recuerda.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "ver_logs",
                "description": "Lee las ultimas N lineas del archivo de log del agente. Usalo para diagnosticar problemas y entender que hizo el agente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lineas": {
                            "type": "integer",
                            "description": "Cuantas lineas leer desde el final. Default: 20."
                        }
                    }
                }
            }
        ]
    }
]
