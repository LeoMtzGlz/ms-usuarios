from django.apps import AppConfig


class ComunConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "comun"

    def ready(self):
        # hu-25/st-184: propaga el bloqueo de Axes al HttpRequest original
        from axes.signals import user_locked_out
        from comun.errores import marcar_bloqueo_en_request_django
        user_locked_out.connect(
            marcar_bloqueo_en_request_django,
            dispatch_uid="st184_bloqueo_drf",
        )
