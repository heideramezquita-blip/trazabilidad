"""Normalización estricta de cifras, sin conversiones silenciosas ×1000."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

class ValueErrorLocal(ValueError):
    pass


def decimal_from_excel(value, decimal_separator='auto') -> Decimal:
    if isinstance(value, bool):
        raise ValueErrorLocal('Se esperaba un número, no SI/NO.')
    if value is None or str(value).strip() == '':
        raise ValueErrorLocal('Celda vacía.')
    if isinstance(value, (int, float, Decimal)):
        source = str(value)
    else:
        source = str(value).strip().replace('\u00a0', '')
        if not re.fullmatch(r'[+-]?[0-9][0-9.,]*', source):
            raise ValueErrorLocal(f'No es número válido: {source!r}.')
        if decimal_separator == 'auto':
            if '.' in source and ',' in source:
                raise ValueErrorLocal('Separadores mezclados: configure decimal_separator.')
            char = ',' if ',' in source else '.'
            if source.count(char) > 1:
                raise ValueErrorLocal('Separadores repetidos: indique un formato inequívoco.')
            if char in source and len(source.split(char)[-1]) == 3:
                raise ValueErrorLocal(f'Número ambiguo {source!r}; configure decimal_separator.')
            source = source.replace(',', '.')
        else:
            char = '.' if decimal_separator == 'dot' else ','
            grouping = ',' if char == '.' else '.'
            if char in source and grouping in source:
                parts = source.split(char)
                if len(parts) != 2 or not re.fullmatch(r'[+-]?\d{1,3}(?:' + re.escape(grouping) + r'\d{3})+', parts[0]):
                    raise ValueErrorLocal('Agrupación/decimal inválidos.')
                source = parts[0].replace(grouping, '') + '.' + parts[1]
            elif grouping in source:
                # Sin separador decimal: admitir agrupación solo si es inequívoca para configuración indicada.
                if not re.fullmatch(r'[+-]?\d{1,3}(?:' + re.escape(grouping) + r'\d{3})+', source):
                    raise ValueErrorLocal('Separador de miles inválido.')
                source = source.replace(grouping, '')
            else:
                source = source.replace(char, '.')
    try:
        result = Decimal(source)
    except InvalidOperation as exc:
        raise ValueErrorLocal(f'Número inválido: {value!r}') from exc
    if not result.is_finite():
        raise ValueErrorLocal('NaN e infinito no se admiten.')
    return result


def normalize_decimal(value, places: int | None, decimal_separator='auto') -> str | None:
    if value is None or str(value).strip() == '':
        return None
    n = decimal_from_excel(value, decimal_separator)
    if places is not None:
        n = n.quantize(Decimal('1').scaleb(-places), rounding=ROUND_HALF_UP)
    if not n:
        n = abs(n)
    return format(n, 'f')


def verify_decimal(web_value: str, expected: str) -> bool:
    if not str(web_value).strip():
        return False
    text = str(web_value).strip()
    if text.count(',') + text.count('.') > 1:
        return False
    try:
        # El sitio debe exponer una única interpretación inequívoca.
        if ',' in text:
            n = decimal_from_excel(text, 'comma')
        else:
            n = decimal_from_excel(text, 'dot')
        return n == Decimal(expected)
    except ValueErrorLocal:
        return False
