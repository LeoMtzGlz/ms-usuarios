import factory

from usuarios.models import Estado, Usuario

PASSWORD_PRUEBA = "Secreta123"

class UsuarioFactory(factory.django.DjangoModelFactory):
    """Usuario activo con contraseña conocida. Cada prueba cambia solo lo que le importa:
    UsuarioFactory(estado=Estado.PENDIENTE), UsuarioFactory(rol=Rol.ADMINISTRADOR)...
    """

    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"usuario{n}@ejemplo.com")
    first_name = "Ana"
    last_name = "López"
    telefono = factory.Sequence(lambda n: f"+52443100{n:04d}")
    estado = Estado.ACTIVO
    email_verificado = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or PASSWORD_PRUEBA)
        if create:
            obj.save(update_fields=["password"])
