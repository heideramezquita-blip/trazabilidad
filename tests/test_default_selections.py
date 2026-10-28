"""Tests sin navegador: valores de inicio no son necesariamente datos ocupados."""
from types import SimpleNamespace
import pytest
from trazabilidad.form_adapter import FormAdapter, FormMismatch

class Element:
    def __init__(self, value, tag='select'):
        self.value = value
        self.tag = tag
    def evaluate(self, _):
        return self.tag


def inspect(fields):
    adapter = FormAdapter.__new__(FormAdapter)
    adapter._rows = lambda title: SimpleNamespace(count=lambda: 1)
    adapter._element = lambda title, index, field, cols: fields[field]
    adapter._get_value = lambda element: element.value
    # No puede haber checkpoints asociados a un formulario nuevo.
    checkpoint = SimpleNamespace(has=lambda *_args: False)
    adapter._existing_mismatch('Panel Principal', [], {f: i for i, f in enumerate(fields)}, checkpoint, resume=False)


def test_selector_rspo_no_is_a_non_occupied_default():
    inspect({'rspo': Element('NO'), 'molino': Element('', 'input')})


def test_automatic_geography_does_not_count_as_existing_editable_data():
    inspect({'rspo': Element('NO'), 'pais': Element('COLOMBIA', 'input'),
             'municipio': Element('MUNICIPIO AUTOMATICO', 'input')})


@pytest.mark.parametrize('fields, expected', [
    ({'rspo': Element('SG')}, 'rspo'),
    ({'rspo': Element('NO'), 'molino': Element('DATOS AJENOS', 'input')}, 'molino'),
    ({'rspo': Element('NO', 'input')}, 'rspo'),
    ({'cpo_tm': Element('0.00', 'input')}, 'cpo_tm'),
    ({'poligonos': Element('SI')}, 'poligonos'),
])
def test_preexisting_editable_data_fails_closed_without_exposing_values(fields, expected):
    with pytest.raises(FormMismatch) as ex:
        inspect(fields)
    assert f'campos: {expected}' in str(ex.value)
    assert 'DATOS AJENOS' not in str(ex.value)
