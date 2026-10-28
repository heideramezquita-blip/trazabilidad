"""Solo interacción visible por controles normales Playwright. No usa APIs internas."""
from __future__ import annotations
import time
from decimal import Decimal
from .excel_reader import normalize_heading
from .models import HEADERS_MILL, HEADERS_PLANT, MILL_FIELDS, PLANT_FIELDS, AUTO_FIELDS, DECIMAL_FIELDS, NUMERIC_OTHER
from .normalize import verify_decimal


class FormMismatch(RuntimeError):
    pass


class FormAdapter:
    def __init__(self, page, config):
        self.page = page
        self.config = config
        self.frame = page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame')
        self.last_date = None
        self.stats = {'conformes': 0, 'diferencias': [], 'automaticos_pendientes': [], 'automaticos_observados': {}, 'avisos_sitio': []}
        self.page.set_default_timeout(config.control_timeout_ms)

    def _tab(self, title):
        label = {'Panel Principal': 'Panel Principal',
                 'Plantaciones Propias': 'Plantaciones Propias',
                 'Plantaciones de Terceros': 'Plantaciones de Terceros'}[title]
        button = self.frame.get_by_role('button', name=label, exact=False)
        if button.count() != 1:
            raise FormMismatch(f'Pestaña {label!r} ausente o duplicada.')
        button.click()

    def _table_selector(self, title):
        return {'Panel Principal': '#table-panel-ext',
                'Plantaciones Propias': '#table-PlantacionesPropias',
                'Plantaciones de Terceros': '#table-PlantacionesdeTerceros'}[title]

    def _table(self, title):
        table = self.frame.locator(self._table_selector(title))
        if table.count() != 1:
            raise FormMismatch(f'Tabla de {title} ausente o duplicada; revisar selectores.')
        return table

    def _columns(self, title):
        table = self._table(title)
        headings = table.locator('thead tr').first.locator('th')
        if not headings.count():
            raise FormMismatch(f'La tabla {title} no tiene encabezados semánticos <thead>.')
        mapping = MILL_FIELDS if title == 'Panel Principal' else PLANT_FIELDS
        expected = HEADERS_MILL if title == 'Panel Principal' else HEADERS_PLANT
        canonical = {normalize_heading(expected[col]): field for col, field in mapping.items()}
        columns = {}
        unknown = []
        for i in range(headings.count()):
            name = normalize_heading(headings.nth(i).inner_text())
            if not name or name in ('numero', 'n', 'acciones', 'accion') or name == normalize_heading('#'):
                continue
            if name not in canonical:
                unknown.append(headings.nth(i).inner_text())
                continue
            key = canonical[name]
            if key in columns:
                raise FormMismatch(f'Columna {key} duplicada en {title}.')
            columns[key] = i
        missing = set(mapping.values()) - set(columns)
        if unknown or missing:
            raise FormMismatch(f'Estructura inesperada {title}: desconocidas={unknown}, faltantes={sorted(missing)}. Ningún campo se escribe.')
        return columns

    def preflight(self, plan, checkpoints, resume=False):
        """Comprueba estructura y periodo antes de escribir un solo dato."""
        body = self.frame.locator('body').inner_text(timeout=self.config.control_timeout_ms)
        if 'EXTRACTORA' not in body.upper():
            raise FormMismatch('No se pudo confirmar el modo EXTRACTORA.')
        period = self.frame.locator('#periodo-reporte')
        if period.count() != 1:
            raise FormMismatch('Periodo de reporte no identificado.')
        actual_period = period.input_value() if period.evaluate('(e) => "value" in e') else period.inner_text()
        if normalize_heading(actual_period) != normalize_heading(plan.period):
            raise FormMismatch(f'Periodo del sitio {actual_period!r} ≠ periodo de Excel {plan.period!r}.')
        date = self.frame.locator('#fecha-actual')
        self.last_date = date.input_value() if date.count() == 1 else None
        for title in ('Panel Principal', 'Plantaciones Propias', 'Plantaciones de Terceros'):
            self._tab(title)
            cols = self._columns(title)
            records = [plan.mill] if title == 'Panel Principal' else (plan.own if title == 'Plantaciones Propias' else plan.third)
            self._existing_mismatch(title, records, cols, checkpoints, resume)
        self._tab('Panel Principal')
        op = self.frame.locator('#nombre-diligenciador')
        if op.count() != 1 or op.is_disabled() or op.is_editable() is False:
            raise FormMismatch('Campo del diligenciador no editable o ausente.')

    def _rows(self, title):
        return self._table(title).locator('tbody tr')

    def _element(self, title, row_index, field, cols):
        rows = self._rows(title)
        if row_index >= rows.count():
            raise FormMismatch(f'Fila web {row_index+1} no existe en {title}.')
        cell = rows.nth(row_index).locator('td').nth(cols[field])
        control = cell.locator('input:not([type="hidden"]), textarea, select')
        return control.first if control.count() == 1 else cell

    @staticmethod
    def _get_value(element):
        tag = element.evaluate('(e) => e.tagName.toLowerCase()')  # Solo lectura, nunca asigna DOM.
        if tag in ('input', 'textarea', 'select'):
            return element.input_value().strip()
        return element.inner_text().strip()

    @staticmethod
    def _same(field, actual, expected):
        actual = str(actual).strip()
        if expected is None:
            return not actual or (field == 'poligonos' and actual == '--')
        if field in DECIMAL_FIELDS or field in NUMERIC_OTHER:
            return verify_decimal(actual, expected)
        if field == 'anio_certificacion' and expected == '0' and actual == '0000':
            return True
        return actual == expected

    def _write(self, title, row_index, field, expected, cols):
        element = self._element(title, row_index, field, cols)
        tag = element.evaluate('(e) => e.tagName.toLowerCase()')
        if tag not in ('input', 'textarea', 'select'):
            raise FormMismatch(f'{title} fila web {row_index+1} campo {field}: no editable.')
        if not element.is_editable():
            raise FormMismatch(f'{title} fila web {row_index+1} campo {field}: readonly.')
        if tag == 'select':
            try:
                element.select_option(label=expected)
            except Exception:
                element.select_option(value=expected)
        else:
            element.fill(expected)
            element.press('Tab')  # Dispara blur sin enviar Enter.
        actual = self._get_value(self._element(title, row_index, field, cols))
        if self._same(field, actual, expected):
            return
        if field in DECIMAL_FIELDS or field in NUMERIC_OTHER:
            # Segundo y último intento: separador decimal alternativo, sujeto a verificación.
            if '.' in expected:
                element = self._element(title, row_index, field, cols)
                element.fill(expected.replace('.', ','))
                element.press('Tab')
                actual = self._get_value(self._element(title, row_index, field, cols))
                if self._same(field, actual, expected):
                    return
        raise FormMismatch(f'{title} fila web {row_index+1} {field}: esperado {expected!r}, observado {actual!r}.')

    def _read_all_fields(self, title, index, record, cols):
        diffs = []
        for field, expected in record.values.items():
            observed = self._get_value(self._element(title, index, field, cols))
            if not self._same(field, observed, expected):
                diffs.append({'sheet': title, 'excel_row': record.excel_row,
                              'field': field, 'message': f'esperado {expected!r}; observado {observed!r}'})
        return diffs

    def _inspect_automatic(self, title, index, record, cols):
        fields = ('tipo', 'municipio', 'departamento', 'pais', 'pct_estimado') if title != 'Panel Principal' else ('municipio', 'departamento', 'pais')
        # Espera acotada, solo tras escribir las coordenadas; no calcula valores del tercero.
        until = time.monotonic() + self.config.automatic_timeout_ms / 1000
        while True:
            missing = [f for f in fields if not self._get_value(self._element(title, index, f, cols))]
            if not missing or time.monotonic() >= until:
                break
            self.page.wait_for_timeout(150)
        self.stats['automaticos_observados'][f'{title} / fila {record.excel_row}'] = {
            field: self._get_value(self._element(title, index, field, cols)) for field in fields
        }
        for field in missing:
            self.stats['automaticos_pendientes'].append(f'{title} fila {record.excel_row}: {field}')

    @staticmethod
    def _known_empty_selection(field, value):
        """Valores iniciales conocidos del selector; NO es el RSPO predeterminado.

        No tratar como vacíos nombres, IDs, volúmenes ni otros valores editables.
        Un selector con SG/MB/IP sigue representando información preexistente.
        """
        return (field == 'rspo' and value == 'NO') or (field == 'poligonos' and value == '--')

    def _existing_mismatch(self, title, records, cols, checkpoints, resume):
        # Inspeccionar antes de escribir; incluso una fila parcialmente llena puede ser del usuario.
        rows = self._rows(title)
        for index in range(rows.count()):
            values = []
            for field in cols:
                if field in AUTO_FIELDS:
                    continue
                element = self._element(title, index, field, cols)
                v = self._get_value(element)
                if not v:
                    continue
                # El selector RSPO puede abrir en NO y el de polígonos en --.
                # Solo son valores iniciales seguros si se trata de un SELECT;
                # no ignorar un texto literal NO que alguien escribió en un input.
                if (self._known_empty_selection(field, v)
                        and element.evaluate('(e) => e.tagName.toLowerCase()') == 'select'):
                    continue
                values.append(field)
            if not values:
                continue
            if not resume or index >= len(records) or not checkpoints.has(records[index], index):
                fields = ', '.join(values)
                raise FormMismatch(
                    f'{title} tiene valores preexistentes en fila web {index+1} '
                    f'(campos: {fields}). No se sobrescriben.')
            diffs = self._read_all_fields(title, index, records[index], cols)
            if diffs:
                raise FormMismatch(f'{title} fila {index+1}: DOM diferente del checkpoint. Detenido sin sobrescribir.')

    def load_panel(self, plan, checkpoints, resume=False):
        self._tab('Panel Principal')
        title = 'Panel Principal'
        cols = self._columns(title)
        self._existing_mismatch(title, [plan.mill], cols, checkpoints, resume)
        input_operator = self.frame.locator('#nombre-diligenciador')
        existing_operator = input_operator.input_value().strip()
        if existing_operator and existing_operator != plan.operator:
            raise FormMismatch('El nombre del diligenciador ya contiene datos incompatibles.')
        if not existing_operator:
            input_operator.fill(plan.operator)
            input_operator.press('Tab')
        if input_operator.input_value().strip() != plan.operator:
            raise FormMismatch('Nombre del diligenciador no verificado.')
        if not (resume and checkpoints.has(plan.mill, 0) and not self._read_all_fields(title, 0, plan.mill, cols)):
            self._fill_row(title, 0, plan.mill, cols)
            checkpoints.save(plan.mill, 0)

    def _fill_row(self, title, index, rec, cols):
        for field, expected in rec.values.items():
            if expected is None:
                continue
            self._write(title, index, field, expected, cols)
        self._inspect_automatic(title, index, rec, cols)
        diffs = self._read_all_fields(title, index, rec, cols)
        if diffs:
            raise FormMismatch(f'{title} fila {rec.excel_row}: no coincide tras rellenar: {diffs}')

    def load_plants(self, title, records, checkpoints, resume=False):
        self._tab(title)
        cols = self._columns(title)
        self._existing_mismatch(title, records, cols, checkpoints, resume)
        for index, record in enumerate(records):
            if index >= self._rows(title).count():
                prev = self._rows(title).count()
                buttons = self.frame.get_by_role('button', name='+ Agregar Fila', exact=False)
                if buttons.count() != 1:
                    raise FormMismatch(f'{title}: botón Agregar Fila ambiguo/ausente.')
                buttons.click()
                if self._rows(title).count() != prev+1:
                    raise FormMismatch(f'{title}: no se añadió exactamente una fila.')
            if resume and checkpoints.has(record, index) and not self._read_all_fields(title, index, record, cols):
                continue
            self._fill_row(title, index, record, cols)
            checkpoints.save(record, index)
            if self.config.pause_between_rows_ms:
                self.page.wait_for_timeout(self.config.pause_between_rows_ms)

    def verify_all(self, plan):
        self.stats['conformes'] = 0
        self.stats['diferencias'] = []
        self.stats['avisos_sitio'] = []
        for title, records in [('Panel Principal', [plan.mill]),
                               ('Plantaciones Propias', plan.own),
                               ('Plantaciones de Terceros', plan.third)]:
            self._tab(title)
            cols = self._columns(title)
            count = self._rows(title).count()
            if count < len(records):
                self.stats['diferencias'].append({'sheet': title, 'excel_row': 0, 'field': 'conteo',
                                                  'message': f'{count} filas web frente a {len(records)} Excel'})
            for index, rec in enumerate(records):
                if index >= count:
                    break
                diffs = self._read_all_fields(title, index, rec, cols)
                if rec.values.get('anio_certificacion') == '0' and self._get_value(self._element(title, index, 'anio_certificacion', cols)) == '0000':
                    self.stats['avisos_sitio'].append(f'{title}, fila Excel {rec.excel_row}: año marcador 0 representado como 0000 en el sitio.')
                self.stats['diferencias'].extend(diffs)
                self.stats['conformes'] += len(rec.values)-len(diffs)
        self._tab('Panel Principal')
        observed_operator = self.frame.locator('#nombre-diligenciador').input_value().strip()
        if observed_operator != plan.operator:
            self.stats['diferencias'].append({'sheet':'Panel Principal','excel_row':7,'field':'diligenciador',
                                               'message':f'esperado {plan.operator!r}; observado {observed_operator!r}'})
        else:
            self.stats['conformes'] += 1
        observed_period = self.frame.locator('#periodo-reporte').input_value()
        if normalize_heading(observed_period) != normalize_heading(plan.period):
            self.stats['diferencias'].append({'sheet':'Panel Principal','excel_row':5,'field':'periodo',
                                               'message':'El periodo del sitio cambió durante la carga.'})
        else:
            self.stats['conformes'] += 1
        return self.stats
