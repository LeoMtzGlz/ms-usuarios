# ST-35: Implementar notificar() y clase base Canal

- **Estado:** Completado
- **Responsable:** Katia Paola Victoria Escalera
- **Descripción:** Se implementó la función central `notificar()` para guardar notificaciones en la bandeja de salida (patrón Outbox) y la clase abstracta `Canal` que servirá de interfaz para los canales de correo y WhatsApp.
- **Resultado:** La prueba unitaria `test_notificar_guarda_en_bandeja` pasa correctamente.