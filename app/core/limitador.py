"""Freno de fuerza bruta por ventana deslizante, en memoria.

Suficiente para un despliegue de un solo proceso, que es el caso de este
proyecto. Con varios workers cada uno llevaria su propia cuenta: ahi tocaria
mover el conteo a Redis o al proxy de entrada.
"""
from collections import defaultdict, deque
from time import monotonic

from app.core.config import settings
from app.core.exceptions import DemasiadosIntentos


class Limitador:
    def __init__(self, intentos: int, ventana_segundos: int):
        self.intentos = intentos
        self.ventana = ventana_segundos
        self._registro: dict[str, deque[float]] = defaultdict(deque)

    def _limpiar(self, marcas: deque[float], ahora: float) -> None:
        while marcas and ahora - marcas[0] > self.ventana:
            marcas.popleft()

    def revisar(self, *claves: str) -> None:
        """Lanza si alguna de las claves agotó su cupo. No consume intentos."""
        ahora = monotonic()
        for clave in claves:
            marcas = self._registro[clave]
            self._limpiar(marcas, ahora)
            if len(marcas) >= self.intentos:
                espera = int(self.ventana - (ahora - marcas[0])) + 1
                raise DemasiadosIntentos(
                    f"Demasiados intentos. Espera {espera} segundos antes de volver a probar."
                )

    def anotar_fallo(self, *claves: str) -> None:
        """Solo cuentan los intentos fallidos: un login correcto no penaliza."""
        ahora = monotonic()
        for clave in claves:
            self._registro[clave].append(ahora)

    def limpiar(self, *claves: str) -> None:
        for clave in claves:
            self._registro.pop(clave, None)

    def reiniciar(self) -> None:
        """Borra todo el conteo. Lo usan las pruebas para no contaminarse entre sí."""
        self._registro.clear()


# Los cupos salen de la configuración, para poder ajustarlos sin tocar código.
limitador_login = Limitador(
    intentos=settings.LOGIN_INTENTOS,
    ventana_segundos=settings.LOGIN_VENTANA_SEGUNDOS,
)
limitador_registro = Limitador(intentos=5, ventana_segundos=600)
