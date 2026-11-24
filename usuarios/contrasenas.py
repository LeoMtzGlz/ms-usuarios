"""HU-15: contraseña temporal para las cuentas que da de alta un administrador."""
import secrets

LONGITUD_TEMPORAL = 12
LONGITUD_MINIMA = 8

# Sin caracteres ambiguos (O/0, I/l/1): la contraseña se le dicta o se le imprime a una persona.
MAYUSCULAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
MINUSCULAS = "abcdefghijkmnopqrstuvwxyz"
NUMEROS = "23456789"
SIMBOLOS = "!@#$%&*-_+="

_GRUPOS = (MAYUSCULAS, MINUSCULAS, NUMEROS, SIMBOLOS)


def generar_contrasena_temporal(longitud: int = LONGITUD_TEMPORAL) -> str:
    """Devuelve una contraseña aleatoria con mayúscula, minúscula, número y símbolo.

    Usa `secrets` (no `random`): el generador es criptográficamente seguro. Cumple
    AUTH_PASSWORD_VALIDATORS (T-12). Quien la llama es responsable de no guardarla
    en texto plano ni escribirla en la bitácora: solo se guarda su hash y se
    devuelve una vez en la respuesta del alta.
    """
    if longitud < LONGITUD_MINIMA:
        raise ValueError(f"La contraseña temporal necesita al menos {LONGITUD_MINIMA} caracteres.")

    # Un carácter de cada grupo garantiza la mezcla; el resto sale de todos los grupos.
    caracteres = [secrets.choice(grupo) for grupo in _GRUPOS]
    todos = "".join(_GRUPOS)
    caracteres += [secrets.choice(todos) for _ in range(longitud - len(caracteres))]

    # Sin el barajado, los cuatro primeros caracteres siempre serían del mismo tipo y orden.
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)
