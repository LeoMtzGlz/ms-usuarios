
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
DOMINIO_CORREO_INSTITUCIONAL = env("DOMINIO_CORREO_INSTITUCIONAL", default="@jiquilpan.tecnm.mx")



# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "drf_spectacular",

    "comun",
    "usuarios",
    "notificaciones",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL") }

# T-24/ST-178 - Database cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email", "first_name", "last_name")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "comun.validadores.MayusculaYNumeroValidator"}, # Validador propio, requerido desde T-12/ST-102
]




# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-mx"

TIME_ZONE = "America/Mexico_City"

USE_I18N = True

USE_TZ = True



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modelo de usuario propio: se define ANTES de la primera migración
AUTH_USER_MODEL = "usuarios.Usuario"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "comun.errores.manejador_errores",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # t-04/st-21: JWT primero, para que una petición sin token responda 401 (no 403)
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
       ),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "loggers": {
        "svc": {"handlers": ["consola"], "level": env("LOG_LEVEL", default="INFO"), "propagate": False},
    },
}

#t-12/st-102
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
SPECTACULAR_SETTINGS = {
    "TITLE": "Servicios de usuario API",
    "DESCRIPTION": "Documentación de la API del microservicio de usuario.",
    "VERSION": "1.0.0"
}

# --- t-05/st-80: Backend de autenticación por correo o teléfono ------------------
# Permite que el login acepte tanto el correo electrónico como el número de 
# teléfono (en formato normalizado). 
AUTHENTICATION_BACKENDS = [
    'usuarios.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]


   # --- t-04/st-21: Tokens JWT firmados con RS256 -------------------------------------
   # La llave privada firma los tokens y solo la tiene este microservicio; la pública
   # la usan los demás servicios para verificarlos. Guía: docs/llaves_rs256_sjwt.md
   # JWT_LLAVE_PRIVADA / JWT_LLAVE_PUBLICA aceptan una ruta (archivo) o el contenido PEM
   # (variable). Si el archivo no existe, la llave queda vacía y el proyecto arranca igual
   # (pruebas, CI, migraciones); solo fallará al firmar o verificar un token.

def leer_llave(variable, por_defecto):
    valor = env(variable, default=por_defecto).strip()
    if valor.startswith("-----BEGIN"):
        return valor.replace("\\n", "\n")
    ruta = Path(valor)
    if not ruta.is_absolute():
        ruta = BASE_DIR / ruta
    return ruta.read_text() if ruta.is_file() else ""


SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": leer_llave("JWT_LLAVE_PRIVADA", "llaves/privada.pem"),
    "VERIFYING_KEY": leer_llave("JWT_LLAVE_PUBLICA", "llaves/publica.pem"),
    "ISSUER": "svc-usuarios",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}
