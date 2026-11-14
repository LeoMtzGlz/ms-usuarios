from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Usuario

from .models import Dispositivo2FA #t-30/st-205


class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email",)


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "telefono", "rol", "estado", "last_login")
    list_filter = ("rol", "estado", "is_staff")
    search_fields = ("email", "first_name", "last_name", "telefono")
    readonly_fields = ("token_version", "last_login", "date_joined", "acepto_privacidad_en")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "telefono", "canal_preferido")}),
        ("Cuenta", {"fields": ("rol", "estado", "email_verificado", "telefono_verificado",
                               "debe_cambiar_password", "token_version")}),
        ("Privacidad", {"fields": ("acepto_privacidad_en", "version_privacidad")}),
        ("Permisos del admin de Django", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)

#t-30/st-205
@admin.register(Dispositivo2FA)
class Dispositivo2FAAdmin(admin.ModelAdmin):
    list_display = ("usuario", "confirmado", "creado_en")
    exclude = ("secreto_cifrado",)