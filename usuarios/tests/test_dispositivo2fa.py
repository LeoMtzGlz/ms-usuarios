
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

from comun.cifrado import cifrar, descifrar
from usuarios.models import Usuario, Dispositivo2FA
import pyotp


class Dispositivo2FATests(TestCase):

    def setUp(self):
        # Generamos una clave Fernet exclusiva para las pruebas.
        self.clave = Fernet.generate_key().decode()

        self.settings_override = override_settings(
            CLAVE_CIFRADO_2FA=self.clave,
            ISSUER_2FA="svc-usuarios",
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        # Creamos un usuario para asociarlo al dispositivo 2FA.
        self.usuario = Usuario.objects.create(
            email="prueba2fa@example.com"
        )

    def test_cifrar_y_descifrar_secreto(self):
        secreto = "JBSWY3DPEHPK3PXP"

        secreto_cifrado = cifrar(secreto)
        secreto_descifrado = descifrar(secreto_cifrado)

        self.assertNotEqual(secreto, secreto_cifrado)
        self.assertEqual(secreto, secreto_descifrado)

    def test_secreto_se_guarda_cifrado_en_base_de_datos(self):
        dispositivo = Dispositivo2FA(usuario=self.usuario)

        secreto = dispositivo.generar_secreto()
        dispositivo.save()

        # Consultamos directamente el valor almacenado.
        secreto_guardado = Dispositivo2FA.objects.values_list(
            "secreto_cifrado",
            flat=True
        ).get(pk=dispositivo.pk)

        self.assertNotEqual(secreto, secreto_guardado)
        self.assertEqual(secreto, dispositivo.secreto)

    def test_verificar_codigo_totp_valido(self):
        dispositivo = Dispositivo2FA(usuario=self.usuario)

        dispositivo.generar_secreto()
        dispositivo.save()

        codigo = pyotp.TOTP(dispositivo.secreto).now()

        self.assertTrue(dispositivo.verificar(codigo))

    def test_rechazar_codigo_totp_incorrecto(self):
        dispositivo = Dispositivo2FA(usuario=self.usuario)

        dispositivo.generar_secreto()
        dispositivo.save()

        codigo_incorrecto = "codigo_invalido"

        self.assertFalse(dispositivo.verificar(codigo_incorrecto))
