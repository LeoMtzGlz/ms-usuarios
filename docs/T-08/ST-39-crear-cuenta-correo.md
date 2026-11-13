# T-08 — Configurar el canal de correo con SMTP

## ST-39. Crear la cuenta de correo del proyecto

**Estado:** Completada  
**Responsable:** Alondra Alejandra López Medellin

### 1. Descripción

Se creó una cuenta de correo electrónico exclusiva para el Microservicio de Usuarios, con el propósito de utilizarla como remitente para el envío de correos electrónicos relacionados con las funcionalidades del sistema.

### 2. Datos de la cuenta

| Campo | Información |
|---|---|
| Proveedor | Gmail |
| Correo electrónico | ITJDAW.Usuarios@gmail.com |
| Nombre de la aplicación | Proyecto Usuarios SMTP |


### 3. Significado del nombre de la cuenta

El nombre de la cuenta se definió considerando la institución, el proyecto y el servicio al que pertenece:

- **ITJ:** Instituto Tecnológico de Jiquilpan.
- **DAW:** Desarrollo de Aplicaciones Web.
- **Usuarios:** Identificación del Microservicio de Usuarios.

### 4. Configuración de seguridad

Para permitir el uso de la cuenta mediante el servicio SMTP, se realizaron las siguientes acciones:

- Creación de una cuenta de Gmail exclusiva para el proyecto.
- Activación de la verificación en dos pasos.
- Generación de una contraseña de aplicación con el nombre **Proyecto Usuarios SMTP**.

La contraseña de aplicación se utilizará para la conexión SMTP cuando sea requerida durante la configuración del servicio.

Por motivos de seguridad, las credenciales no se incluyen en esta documentación. En caso de ser necesarias para otro integrante del equipo, se compartirán por un medio privado.

### 5. Resultado

La cuenta de correo del proyecto fue creada y cuenta con la configuración de seguridad necesaria para continuar con la integración del canal de correo SMTP.

**ST-39 finalizada.**

**Responsable de la actividad:** alondraLopez.