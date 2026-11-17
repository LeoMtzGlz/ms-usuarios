from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        from usuarios import privacidad  # registra la revisión de VERSION_AVISO_PRIVACIDAD (t-02/st-67)