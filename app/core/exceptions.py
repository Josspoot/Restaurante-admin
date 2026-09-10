"""Excepciones de dominio.

Los servicios lanzan estas excepciones sin saber nada de HTTP; main.py las
traduce a codigos de estado. Es el equivalente a @ControllerAdvice en Spring.
"""


class ErrorDominio(Exception):
    """Base de todos los errores de negocio."""

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


class RecursoNoEncontrado(ErrorDominio):
    """El recurso solicitado no existe -> 404."""


class ReglaDeNegocio(ErrorDominio):
    """La operacion es invalida en el estado actual -> 409."""


class NoAutorizado(ErrorDominio):
    """Credenciales invalidas o token expirado -> 401."""


class PermisoDenegado(ErrorDominio):
    """El usuario esta autenticado pero su rol no alcanza -> 403."""


class DemasiadosIntentos(ErrorDominio):
    """Se agoto el cupo de intentos en la ventana de tiempo -> 429."""
