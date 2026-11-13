from django.contrib.auth.base_user import BaseUserManager

from usuarios.telefono import normalizar_telefono


class UsuarioManager(BaseUserManager):
    """Crea usuarios usando el correo como identificador (no hay username)."""

    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio.")
        email = self.normalize_email(email).strip().lower()
        if extra.get("telefono"):
            extra["telefono"] = normalizar_telefono(extra["telefono"])
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)  # guarda el hash, nunca el texto plano
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        from usuarios.models import Estado, Rol

        extra.update(
            is_staff=True,
            is_superuser=True,
            rol=Rol.ADMINISTRADOR, # USR-121 - Ajuste para incorporacion de rol
            estado=Estado.ACTIVO,
            is_active=True,
            email_verificado=True,
        )
        return self._crear(email, password, **extra)
