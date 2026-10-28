from decimal import Decimal
import pytest
from trazabilidad.normalize import normalize_decimal, decimal_from_excel, verify_decimal, ValueErrorLocal

@pytest.mark.parametrize('source,places,expected', [
    (102.83419,2,'102.83'), (15.578,2,'15.58'), (1.005,2,'1.01'),
    (3.4869034155,6,'3.486903'),(-73.5440480795,6,'-73.544048'),
    (0,2,'0.00'), (-0.00001,2,'0.00'), (None,2,None),
    (Decimal('5.0006'),2,'5.00'), ('15,578',2,'15.58'),
])
def test_rounding(source,places,expected):
    sep = 'comma' if source == '15,578' else 'auto'
    assert normalize_decimal(source,places,sep) == expected

@pytest.mark.parametrize('value', ['1.234', '1,234', '1.2.3', '3 TM', float('inf'), 'NaN'])
def test_ambiguous_or_invalid(value):
    with pytest.raises(ValueErrorLocal):
        decimal_from_excel(value)

def test_configured_separators():
    assert decimal_from_excel('1.234,50','comma') == Decimal('1234.50')
    assert decimal_from_excel('1,234.50','dot') == Decimal('1234.50')
    assert verify_decimal('15,58','15.58')
    assert not verify_decimal('1558','15.58')
    assert not verify_decimal('15.578','15.58')
