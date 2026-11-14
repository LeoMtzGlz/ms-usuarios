import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from comun.roles import Rol # USR-121 - importacion de rol desde comun

from usuarios.managers import UsuarioManager
from usuarios.telefono import validar_telefono_e164

from comun.eventos import registrar_evento

#t-30/st-205
import pyotp
from django.conf import settings
from comun.cifrado import cifrar, descifrar
#-------------

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
            # USR-121 - Garantiza la integridad del rol
            models.CheckConstraint(
                condition=models.Q(rol__in=Rol.values),
                name="usuario_rol_valido",
            ),
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
        
class Proposito(models.TextChoices):
        ACTIVACION = "activacion", "Activación de cuenta"
        RECUPERACION = "recuperacion", "Recuperación de contraseña"
        CAMBIO_CONTACTO = "cambio_contacto", "Cambio de correo o teléfono"

class CodigoVerificacion(models.Model):
    """Código de 6 dígitos de un solo uso. Solo se guarda su hash, nunca el código."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="codigos")
    proposito = models.CharField(max_length=20, choices=Proposito.choices)
    canal = models.CharField(max_length=10, choices=Canal.choices)
    codigo_hash = models.CharField(max_length=128)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado = models.BooleanField(default=False)
    intentos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "código de verificación"
        verbose_name_plural = "códigos de verificación"
        indexes = [
            models.Index(fields=["usuario", "proposito", "usado"], name="codigo_usuario_prop_idx"),
        ]

    def __str__(self):
        return f"{self.proposito} · {self.usuario}"

#t-30/st-205
class Dispositivo2FA(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dispositivo_2fa",
    )
    secreto_cifrado = models.TextField()
    confirmado = models.BooleanField(default=False)
    ultimo_intervalo = models.BigIntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    confirmado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"2FA de {self.usuario_id} (confirmado={self.confirmado})"

    @property
    def secreto(self) -> str:
        return descifrar(self.secreto_cifrado)

    def generar_secreto(self) -> str:
        """Crea un secreto nuevo, lo guarda cifrado y lo devuelve en claro."""
        secreto = pyotp.random_base32()
        self.secreto_cifrado = cifrar(secreto)
        self.confirmado = False
        self.confirmado_en = None
        self.ultimo_intervalo = None
        return secreto

    def uri_aprovisionamiento(self) -> str:
        return pyotp.TOTP(self.secreto).provisioning_uri(
            name=self.usuario.email,
            issuer_name=settings.ISSUER_2FA,
        )

    def verificar(self, codigo: str) -> bool:
        return pyotp.TOTP(self.secreto).verify(codigo, valid_window=1)