from django.db import models

"""
T-13 Roles base del microservicio ms-usuarios.
USR-121 — Crear el enum Rol con TextChoices

- El enum permanecera en comun/roles.py, no en usuarios/models.py, 
  para que comun/permisos.py lo importe sin importaciones circulares.
"""
class Rol(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    CLIENTE = "cliente", "Cliente"
    OPERATIVO = "operativo", "Operativo"