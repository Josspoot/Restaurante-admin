from sqlalchemy import select

from app.models import Usuario
from app.repositories.base import RepositorioBase


class UsuarioRepo(RepositorioBase[Usuario]):
    modelo = Usuario

    def por_email(self, email: str) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.email == email.lower()))
