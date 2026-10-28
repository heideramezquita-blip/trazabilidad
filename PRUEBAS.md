# Estado de verificación — 27/10/2026

## Validación efectuada en entorno de desarrollo

- **24 pruebas unitarias superadas** con `pytest` tras los últimos cambios del lector y generador.
- Lectura de **73 filas propias y 275 de terceros**, sin truncamiento.
- Duplicados de ID, cero frente a vacío, precisión decimal con `ROUND_HALF_UP`, coordenadas, años múltiples/0, encabezados inválidos, fórmulas sin caché y no modificación del Excel original.
- Generación de una plantilla `.xlsx` con datos **ficticios** y ejecución de `validar` aprobada. Esta operación no abre navegador.
- Las **cinco pruebas de integración de navegador** se ejecutaron por separado durante el desarrollo y superaron sus verificaciones: las tres pestañas sin envío, rechazo de datos preexistentes, reanudación con página vacía, fallo controlado ante cambios de encabezados y mitigación comprobada del factor ×1000. No se ha vuelto a ejecutar el conjunto completo de pruebas de navegador en una misma sesión después de la última corrección de plantilla.
- El simulador utiliza dos iframes y un botón de envío instrumentado cuyo contador debe permanecer en 0.

## No verificado

- Instalación de `instalar.bat` en un Windows 10/11 real (el desarrollo se realizó en Linux).
- Compatibilidad con **la interfaz real** de Google Apps Script del tercero: no se proporcionó su URL autorizada ni sesión de prueba. El formulario de pruebas es sintético; la estructura puede variar.
- Comportamiento de cientos de filas cargadas en un navegador real; el test de 73+275 cubre lectura y validación del Excel, mientras que el test de navegador cubre una muestra de filas.
- Autenticación, geocodificación, selectores definitivos y posibles restricciones corporativas de Edge.
- Envío final: **intencionalmente no implementado**. El usuario debe revisar y pulsar manualmente el botón del tercero.

## Recomendación operativa

La primera prueba autorizada debe utilizar pocos registros verdaderos, sin pulsar Enviar hasta verificar los campos y totales. No utilizar el ejemplo ficticio para enviar información al tercero. Conservar siempre los informes locales y el Excel original.
