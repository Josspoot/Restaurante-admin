"""Carga datos de ejemplo para poder probar la API de inmediato.

Uso:  python seed.py
"""
from decimal import Decimal

from app.core.database import SessionLocal, crear_tablas
from app.core.security import hashear_password
from app.models import Categoria, Producto, RolUsuario, Usuario

USUARIOS = [
    ("Administrador", "admin@restaurante.com", "admin123", RolUsuario.ADMIN),
    ("Ana Mesera", "mesero@restaurante.com", "mesero123", RolUsuario.MESERO),
    ("Cliente Demo", "cliente@correo.com", "cliente123", RolUsuario.CLIENTE),
]

MENU = {
    ("Entradas", "Para empezar la comida"): [
        ("Guacamole con totopos", "Aguacate, jitomate, cebolla y cilantro", "89.00"),
        ("Queso fundido con chorizo", "Servido con tortillas de harina", "115.00"),
        ("Sopa de tortilla", "Caldo de jitomate, aguacate y queso", "78.00"),
    ],
    ("Platos fuertes", "Nuestras especialidades"): [
        ("Tacos al pastor (orden de 5)", "Con piña, cebolla y cilantro", "135.00"),
        ("Cochinita pibil", "Marinada en achiote, con cebolla morada", "165.00"),
        ("Arrachera 300g", "Con frijoles charros y guacamole", "289.00"),
        ("Enchiladas verdes", "Rellenas de pollo, crema y queso fresco", "142.00"),
    ],
    ("Bebidas", "Frías y calientes"): [
        ("Agua de horchata 1L", "Preparada en casa", "55.00"),
        ("Limonada mineral", "Con hierbabuena", "45.00"),
        ("Cerveza artesanal", "IPA local 355ml", "75.00"),
        ("Café de olla", "Con canela y piloncillo", "42.00"),
    ],
    ("Postres", "El cierre perfecto"): [
        ("Flan napolitano", "Receta de la casa", "68.00"),
        ("Churros con cajeta", "Orden de 4 piezas", "72.00"),
    ],
}


def main() -> None:
    crear_tablas()
    db = SessionLocal()
    try:
        if db.query(Usuario).count():
            print("La base de datos ya tiene información. Borra restaurante.db para recargarla.")
            return

        for nombre, email, password, rol in USUARIOS:
            db.add(
                Usuario(
                    nombre=nombre,
                    email=email,
                    hashed_password=hashear_password(password),
                    rol=rol,
                )
            )

        productos = 0
        for (nombre_cat, descripcion), platillos in MENU.items():
            categoria = Categoria(nombre=nombre_cat, descripcion=descripcion)
            for nombre_prod, desc_prod, precio in platillos:
                categoria.productos.append(
                    Producto(nombre=nombre_prod, descripcion=desc_prod, precio=Decimal(precio))
                )
                productos += 1
            db.add(categoria)

        db.commit()
        print(f"Listo: {len(USUARIOS)} usuarios, {len(MENU)} categorías y {productos} productos.")
        print("\nCuentas de prueba:")
        for nombre, email, password, rol in USUARIOS:
            print(f"  {rol.value:<8} {email:<28} {password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
