# Cargador local de trazabilidad (Windows 10/11, 64 bits)

**Versión 0.1.0 — prototipo funcional sujeto a verificación con la interfaz real.**

Lee una plantilla Excel con **Panel Principal**, **Plantaciones Propias** y **Plantaciones de Terceros**, normaliza números, valida sin navegador, y luego utiliza **Playwright** para introducir datos en una **ventana propia y visible de Microsoft Edge** o Chromium. Comprueba los campos, guarda informes y deja la ventana abierta para que **una persona revise y decida si envía**.

**El programa NUNCA pulsa «COMPLETAR Y ENVIAR», nunca ejecuta el envío del sitio ni envía HTTP directo.** No sube shapefiles. El hecho de rellenar los controles puede transmitir información al tercero antes de que pulses Enviar (el propio sitio puede consultar ubicaciones). **Validar** no abre navegador ni transmite datos.

## 1. Primera instalación

1. Descarga el repositorio desde GitHub: `Code` → `Download ZIP`; extrae **toda** la carpeta en una ubicación local. No lo ejecutes dentro del ZIP.
2. Instala [Python 3.13 de 64 bits](https://www.python.org/downloads/windows/) si aún no está instalado. Se requiere Python 3.13.x; **no** es necesario administrador para Python por usuario.
3. Haz doble clic en **`instalar.bat`**. Crea `.venv` e instala dependencias desde PyPI; necesita Internet solo durante la instalación. No cambia políticas de PowerShell.
4. Para utilizar **Microsoft Edge ya instalado**, no se requiere descargar otro navegador. Para usar Chromium, ejecuta una sola vez `.venv\Scripts\python.exe -m playwright install chromium` y modifica `browser = "chromium"`.
5. Copia `config.example.toml` como **`config.local.toml`**. Sustituye el marcador de la URL por la URL HTTPS privada del Apps Script autorizado. **No compartas este archivo** ni lo subas a GitHub.

La URL solo se utiliza para la carga autorizada. El programa no añade servicios externos ni telemetría. La sesión de Edge se crea en `.local/browser-profile`, distinta a tu Edge habitual.

## 2. Utilización diaria

1. Haz doble clic en **`validar.bat`**, elige el `.xlsx`. Se revisan estructura, coordenadas, nombres, ceros, duplicados, años y decimales. Consulta los informes en `.local/reports`.
2. Corrige los errores **ERROR**. Las incidencias **AVISO** no impiden cargar. Vuelve a validar después de cualquier modificación: se comprueba el SHA-256 del Excel y no se acepta una validación anterior.
3. Haz doble clic en **`cargar.bat`**, selecciona **el mismo archivo**, lee la advertencia y escribe exactamente `CARGAR`.
4. Se abre una ventana visible separada. Si aparece autenticación, CAPTCHA o un aviso del navegador, resuélvelo manualmente sin eludirlo. El programa solo usa controles normales. Si la estructura o el periodo han cambiado, se detiene.
5. Al terminar, abre el último `.md` y `.csv` de `.local/reports`. Comprueba las coincidencias, ubicación automática, volúmenes, polígonos y fecha del sitio.
6. **Solo tú** decides si pulsas «COMPLETAR Y ENVIAR». Cuando hayas terminado, vuelve a la consola y pulsa INTRO para cerrar **solo la ventana creada por el programa**.

**Importante:** el formulario puede mantener datos únicamente en memoria hasta que se envía. Cerrar o recargar puede perderlos. El informe **no demuestra que se hayan enviado**.

## 3. Comandos equivalentes

Ejecuta desde la carpeta del proyecto en `cmd.exe`:

```bat
set "PYTHONPATH=%CD%\src"
.venv\Scripts\python.exe -m trazabilidad.cli validar --file "C:\Datos\Mi plantilla.xlsx"
.venv\Scripts\python.exe -m trazabilidad.cli cargar --file "C:\Datos\Mi plantilla.xlsx"
.venv\Scripts\python.exe -m trazabilidad.cli reanudar --file "C:\Datos\Mi plantilla.xlsx"
.venv\Scripts\python.exe -m trazabilidad.cli plantilla --output "C:\Datos\plantilla_v2.xlsx"
.venv\Scripts\python.exe -m trazabilidad.cli plantilla --output "C:\Datos\ficticio.xlsx" --ejemplo-ficticio
.venv\Scripts\python.exe -m pytest
```

También dispones de `reanudar.bat` y `pruebas.bat`. Los parámetros `--config RUTA` y `--url URL` se indican **antes** del subcomando. Evita `--url`: podría quedar en el historial de comandos.

Para `reanudar`, no basta con tener un checkpoint: se compara el **DOM real** de cada fila. Si la página quedó vacía, se reconstruye; si contiene valores incompatibles, se detiene sin sobreescribir. En ningún momento se usa almacenamiento oculto del sitio como fuente de verdad.

## 4. Reglas y decisiones sobre Excel

- **Panel Principal:** `C5` periodo, `C6` fecha de referencia, `C7` diligenciador, encabezados en fila 10 y **único molino en fila 11**; las instrucciones de fila 14 en adelante se ignoran.
- **Plantaciones:** encabezados en fila 5 y registros desde fila 6; se recorre hasta la última fila con datos, sin límite de 100 ni truncar la tabla.
- La numeración, tipo de productor, departamento, municipio, país y porcentaje estimado los controla el **sitio**, no este programa.
- Certificación RSPO: `NO`, `MB`, `SG`, `IP`. Polígonos: `SI`, `NO` o vacío. Los polígonos `SI` requieren adjuntar manualmente.
- Volúmenes TM se normalizan a **2 decimales** y coordenadas a **6**, usando `Decimal` y `ROUND_HALF_UP`. `0` es distinto de vacío. El área no se redondea por defecto. La suma se hace **después** de normalizar cada fila, y el informe conserva suma original y diferencia.
- El texto `1.234` o `1,234` es ambiguo: configura explícitamente `decimal_separator = "dot"` o `"comma"` cuando corresponda. **Nunca se interpreta ×1000 en silencio**.
- Los identificadores, incluso repetidos, se preservan. Para ceros iniciales, utiliza **celdas de texto**. Si un número tiene formato simple `00000`, también se rescata su longitud visual; formatos complejos no se adivinan.
- Los años deben ser una única cifra de 4 dígitos. **2019 para propias** es solo un ejemplo de decisión documentada, nunca un valor universal. Para años `0` de terceros, `third_zero_year` debe seleccionarse expresamente entre `empty` y `preserve`. En caso contrario, la validación se bloquea.
- Celdas con fórmulas sin caché se bloquean. Abre el documento en Excel, recalcula, guarda y vuelve a validar. No se ejecutan macros ni instrucciones en las celdas.
- Si ambos porcentajes del molino están presentes y no suman 100, aparece una advertencia, pero nunca se cambian unilateralmente.

## 5. Límites importantes

**La estructura HTML del tercero puede cambiar.** Los selectores se basan en el formulario descrito en las instrucciones: iframes `#sandboxFrame > #userHtmlFrame`, tablas `#table-panel-ext`, `#table-PlantacionesPropias`, `#table-PlantacionesdeTerceros` y encabezados del Excel. Cualquier discrepancia detiene el proceso **antes de colocar valores incorrectos**. La automatización **no se ha validado contra el formulario real**, porque no se dispone de su URL ni de una sesión autorizada en este proyecto. La página HTML de pruebas es ficticia. La primera ejecución autorizada debe realizarse con **pocas filas**; nunca enviar un registro de prueba.

No se evaden autenticaciones ni CAPTCHA. No se usan `google.script.run`, funciones internas, endpoints ocultos ni asignación de DOM por JavaScript. El sitio puede bloquear un perfil automatizado por políticas corporativas. La carga no promete reutilizar una ventana Edge cualquiera que ya esté abierta.

Los archivos reales, informes, perfiles, URL privada, capturas y checkpoints no se publican en Git. Los ficheros de salida permanecen en tu PC.

## 6. Fallos frecuentes

| Situación | Qué hacer |
|---|---|
| `Python 3.13` no encontrado | Instala [Python 3.13 de 64 bits](https://www.python.org/downloads/windows/) y repite `instalar.bat` |
| `msedge` no arranca | Comprueba que Edge esté instalado; políticas corporativas pueden impedir control automatizado. Alternativa: instala Chromium y cambia `browser` |
| Chromium: ejecutable no localizado | Ejecuta `.venv\Scripts\python.exe -m playwright install chromium` |
| No encuentra una tabla/control | El formulario cambió: no fuerces la carga; conserva informe y revisa selectores |
| Periodo no coincide | Selecciona un Excel del periodo correcto; no fuerces campos readonly |
| Datos preexistentes | Usa `reanudar.bat` solo si el DOM coincide con el checkpoint, o abre una sesión realmente vacía |
| Números ×1000 o años `0000` | Revisa informe, separadores y decisiones humanas antes de continuar |
| No se abre el selector de Excel | Utiliza `validar.bat --file "C:\ruta\archivo.xlsx"` |

## 7. Actualizaciones sin perder información

Con ZIP: extrae la nueva versión en **otra carpeta**, pero **antes** copia con precaución `config.local.toml` y tu directorio `.local` al mismo lugar relativo en la nueva carpeta. **No publiques estos archivos.** Si una ventana tiene datos sin enviar, no actualices ni la cierres. Con Git: conserva los archivos ignorados localmente, actualiza el código (`git pull`) y, si cambian dependencias, repite `instalar.bat`. Mantén un respaldo privado de configuración e informes.

## 8. Qué se ha probado

- Se incluyen pruebas `pytest` de la lectura, validaciones, cifras, años, duplicados y un simulador HTML **local** con doble iframe, tres pestañas, edición de filas y contador de envío.
- Los tests de navegador requieren Chromium local en entorno de pruebas; si no existe, se omiten con explicación. El navegador real siempre se ejecuta visible para cargar datos del tercero.
- Estas pruebas **no sustituyen** una validación contra el formulario real. No existe ninguna prueba que envíe un formulario real.

**Dependencias fijadas:** Python 3.13; `openpyxl==3.1.5`; `playwright==1.57.0`; `pytest==9.0.2`; `tzdata==2026.2` para zonas horarias en Windows. Se fijan versiones presentes y comprobadas en el entorno de desarrollo. El paquete Playwright dispone de versiones más recientes; actualizar las dependencias implica repetir pruebas antes de distribuir.


## 9. Detección de formulario nuevo: corrección del 28/10/2026

Algunos formularios muestran la selección inicial `NO` en el desplegable RSPO. La comprobación de datos preexistentes ahora reconoce `NO` en un **selector** RSPO y `--` en un selector de polígonos como valores iniciales compatibles con una fila vacía. No descarta información de otros campos editables. Sigue bloqueando datos reales preexistentes y no permite enviar el formulario.

Si una fila todavía aparece como ocupada, el mensaje indica los **nombres de los campos** que provocan el bloqueo, sin mostrar sus valores. No borres ni sobrescribas esos datos sin revisarlos. Esta corrección está cubierta por pruebas unitarias y **todavía requiere comprobarse en el formulario real**.

Para actualizar una instalación descargada como ZIP sin reinstalar dependencias, reemplaza únicamente `src/trazabilidad/form_adapter.py` por el archivo de la rama `main` del repositorio. Cierra primero cualquier ventana del cargador y conserva `config.local.toml` y `.local/`.
