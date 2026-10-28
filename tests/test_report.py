import csv
import json

from trazabilidad.models import Issue, Plan
from trazabilidad.report import write_report


def test_report_groups_warnings_and_keeps_full_detail(tmp_path):
    plan = Plan(str(tmp_path / 'datos.xlsx'), 'hash-ficticio')
    plan.period = 'Q3 - 2026'
    plan.issues.append(Issue('ERROR', 'Plantaciones Propias', 107, 'plantacion',
                             'Identificación local obligatoria.'))
    for index in range(582):
        plan.issues.append(Issue('AVISO', 'Plantaciones de Terceros', index + 6,
                                 'poligonos', 'Adjuntar polígonos manualmente.'))
    plan.totals = {'propias': {'registros': 1,
                               'tm_original': '112125.580000000026',
                               'tm_original_redondeada_al_final': '112125.58',
                               'tm_normalizada': '112125.58',
                               'diferencia': '-0.000000000026'}}
    output = write_report(plan, tmp_path)
    summary = output.read_text(encoding='utf-8')
    assert '## Errores bloqueantes' in summary
    assert 'fila 107' in summary
    assert '(582 casos)' in summary
    assert '112125.580000000026' not in summary
    assert '| Plantaciones Propias | 1 | 112125.58 |' in summary
    assert len(summary.splitlines()) < 45
    full = json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
    assert len(full['incidencias']) == 583
    assert full['totales']['propias']['diferencia'] == '-0.000000000026'
    with output.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as f:
        assert len(list(csv.reader(f))) == 584