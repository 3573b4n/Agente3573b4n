import json
from pathlib import Path


class Notas:
    """Notas personales persistentes en notas.json.

    El estado vive en el objeto: al crear la instancia se carga el JSON
    una sola vez y los metodos operan sobre memoria.
    """

    def __init__(self, archivo: str = "notas.json"):
        self.archivo = Path(__file__).parent / archivo
        if not self.archivo.exists():
            self.archivo.write_text("[]", encoding="utf-8")
        self._datos = json.loads(self.archivo.read_text(encoding="utf-8"))

    def listar(self) -> list[str]:
        return list(self._datos)

    def agregar(self, texto: str) -> str:
        if not texto.strip():
            return "ERROR: texto vacio, no se puede agregar"
        self._datos.append(texto.strip())
        self._guardar()
        return f"OK: nota {len(self._datos)} agregada"

    def borrar(self, indice: int) -> str:
        if not self._datos:
            return "ERROR: no hay notas para borrar"
        if indice is None:
            return "ERROR: falta indice para borrar"
        if indice < 1 or indice > len(self._datos):
            return f"ERROR: indice {indice} fuera de rango (1-{len(self._datos)})"
        borrada = self._datos.pop(indice - 1)
        self._guardar()
        return f"OK: nota {indice} borrada ('{borrada}')"

    def _guardar(self) -> None:
        self.archivo.write_text(
            json.dumps(self._datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
