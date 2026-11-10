import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from usuarios.managers import UsuarioManager
from usuarios.telefono import validar_telefono_e164

from comun.eventos import registrar_evento

class Rol(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    CLIENTE = "cliente", "Cliente"
    OPERATIVO = "operativo", "Operativo"


class Estado(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de activar"
    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"


class Canal(models.TextChoices):
    CORREO = "correo", "Correo"
    WHATSAPP = "whatsapp", "WhatsApp"


class Usuario(AbstractUser):
    """Usuario del microservicio. El correo es el identificador; no hay username.

    `estado` distingue "falta activar" (pendiente) de "desactivado por el admin" (inactivo).
    `is_active` lo sigue existiendo porque Django y SimpleJWT lo consultan, pero solo
    lo modifica `cambiar_estado()`: is_active == (estado != inactivo).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField("correo", unique=True)
    telefono = models.CharField(
        "teléfono", max_length=16, unique=True, null=True, blank=True, validators=[validar_telefono_e164]
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CLIENTE)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    canal_preferido = models.CharField(max_length=10, choices=Canal.choices, default=Canal.CORREO)
    email_verificado = models.BooleanField(default=False)
    telefono_verificado = models.BooleanField(default=False)
    debe_cambiar_password = models.BooleanField(default=False)
    token_version = models.PositiveIntegerField(
        default=0, help_text="Al incrementarse invalida todas las sesiones del usuario."
    )
    acepto_privacidad_en = models.DateTimeField(null=True, blank=True)
    version_privacidad = models.CharField(max_length=20, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            # Defensa en la base: "Ana@x.com" y "ana@x.com" no pueden coexistir
            models.UniqueConstraint(Lower("email"), name="email_unico_ci"),
        ]
        indexes = [
            models.Index(fields=["estado"], name="usuario_estado_idx"),
            models.Index(fields=["rol"], name="usuario_rol_idx"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def cambiar_estado(self, nuevo: str, por=None) -> None:
        """Único lugar que cambia estado, is_active y token_version.

        - pendiente y activo dejan is_active=True (el login revisa `estado` para
          responder cuenta_pendiente con un mensaje propio).
        - inactivo pone is_active=False e incrementa token_version, lo que cierra
          todas las sesiones abiertas.
        """
        if nuevo not in Estado.values:
            raise ValueError(f"Estado desconocido: {nuevo}")
        self.estado = nuevo
        self.is_active = nuevo != Estado.INACTIVO
        campos = ["estado", "is_active"]
        if nuevo == Estado.INACTIVO:
            self.token_version += 1
            campos.append("token_version")
        anterior = type(self).objects.filter(pk=self.pk).values_list("estado", flat=True).first()
        self.save(update_fields=campos)
        registrar_evento("estado_cambiado", self, anterior=anterior, nuevo=nuevo, por=getattr(por, "pk", None))

