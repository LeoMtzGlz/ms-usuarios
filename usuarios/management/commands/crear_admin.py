"""t-13/st-124: Crear el comando crear_admin <correo>.

Crea una cuenta con rol Administrador. Es la única forma de crear un administrador:
la API no lo permite (T-13, criterios 1 y 4). La contraseña se pide por consola y
debe cumplir la política de T-12.

Uso:
    docker compose run --rm api python manage.py crear_admin admin@ejemplo.com
    docker compose run --rm api python manage.py crear_admin admin@ejemplo.com \
        --nombre Ana --apellidos "López" --telefono "443 123 4567"
"""

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from comun.eventos import registrar_evento
from usuarios.telefono import normalizar_telefono

INTENTOS_MAXIMOS = 3


class Command(BaseCommand):
    help = "Crea una cuenta con rol Administrador. La contraseña se pide por consola."

    def add_arguments(self, parser):
        parser.add_argument("correo", help="Correo del administrador")
        parser.add_argument("--nombre", default="", help="Nombre(s)")
        parser.add_argument("--apellidos", default="", help="Apellidos")
        parser.add_argument("--telefono", default=None, help="Teléfono; se guarda en formato E.164 (+52...)")

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        correo = Usuario.objects.normalize_email(opciones["correo"]).strip().lower()

        if Usuario.objects.filter(email__iexact=correo).exists():
            raise CommandError(f"Ya existe una cuenta con el correo {correo}.")

        datos = {"first_name": opciones["nombre"], "last_name": opciones["apellidos"]}
        if opciones["telefono"]:
            try:
                datos["telefono"] = normalizar_telefono(opciones["telefono"])
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error
            if Usuario.objects.filter(telefono=datos["telefono"]).exists():
                raise CommandError(f"Ya existe una cuenta con el teléfono {datos['telefono']}.")

        password = self._pedir_password(Usuario(email=correo, **datos))

        try:
            with transaction.atomic():
                # create_superuser ya pone rol administrador, estado activo,
                # correo verificado, is_staff e is_superuser (T-02 y st-121).
                admin = Usuario.objects.create_superuser(email=correo, password=password, **datos)
                registrar_evento("admin_creado", admin, origen="comando crear_admin")
        except IntegrityError as error:
            raise CommandError("No se pudo crear la cuenta: el correo o el teléfono ya existen.") from error

        self.stdout.write(self.style.SUCCESS(f"Administrador {correo} creado."))

    def _pedir_password(self, usuario_temporal):
        """Pide la contraseña dos veces y la valida con la política de T-12."""
        for _ in range(INTENTOS_MAXIMOS):
            password = getpass.getpass("Contraseña: ")
            confirmacion = getpass.getpass("Confirma la contraseña: ")
            if password != confirmacion:
                self.stderr.write("Las contraseñas no coinciden.")
                continue
            try:
                validate_password(password, user=usuario_temporal)
            except ValidationError as error:
                self.stderr.write("\n".join(error.messages))
                continue
            return password
        raise CommandError("Demasiados intentos. No se creó la cuenta.")
