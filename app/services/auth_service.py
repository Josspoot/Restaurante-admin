from sqlalchemy.orm import Session

from app.core.exceptions import NoAutorizado, ReglaDeNegocio
from app.core.security import crear_token, hashear_password, quemar_tiempo, verificar_password
from app.models import RolUsuario, Usuario
from app.repositories import UsuarioRepo
from app.schemas.usuario import UsuarioCrear, UsuarioRegistro


class AuthService:
    def __init__(self, db: Session):
        self.repo = UsuarioRepo(db)

    def registrar(self, datos: UsuarioRegistro, rol: RolUsuario = RolUsuario.CLIENTE) -> Usuario:
        email = datos.email.lower()
        if self.repo.por_email(email):
            raise ReglaDeNegocio(f"El correo {email} ya está registrado")
        usuario = Usuario(
            nombre=datos.nombre.strip(),
            email=email,
            hashed_password=hashear_password(datos.password),
            rol=rol,
        )
        return self.repo.guardar(usuario)

    def crear_desde_admin(self, datos: UsuarioCrear) -> Usuario:
        return self.registrar(datos, rol=datos.rol)

    def autenticar(self, email: str, password: str) -> Usuario:
        usuario = self.repo.por_email(email)

        # Mismo mensaje y mismo tiempo de respuesta para "no existe" y para
        # "existe pero la contrasena esta mal": ni el texto ni el reloj deben
        # revelar que correos estan registrados.
        if not usuario:
            quemar_tiempo()
            raise NoAutorizado("Correo o contraseña incorrectos")
        if not verificar_password(password, usuario.hashed_password):
            raise NoAutorizado("Correo o contraseña incorrectos")
        if not usuario.activo:
            raise NoAutorizado("La cuenta está desactivada")
        return usuario

    @staticmethod
    def emitir_token(usuario: Usuario) -> str:
        return crear_token(sub=str(usuario.id), rol=usuario.rol.value)
