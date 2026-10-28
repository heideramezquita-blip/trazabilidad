"""Informe local; nunca implica que el tercero haya recibido los datos."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import csv
import json
from .models import Plan


def local_now():
    try:
        return datetime.now(ZoneInfo('America/Bogota')).isoformat(timespec='seconds')
    except Exception:
        return datetime.now().astimezone().isoformat(timespec='seconds')


def write_report(plan: Plan, report_dir, phase='VALIDACION', verification=None, site_date=None):
    target = Path(report_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    base = target / f'trazabilidad_{stamp}'
    payload = {
        'fase': phase, 'estado': 'NO ENVIADO POR EL PROGRAMA',
        'fecha_informe': local_now(), 'archivo': plan.file_path,
        'sha256': plan.file_sha256, 'periodo': plan.period,
        'fecha_archivo': plan.file_date, 'fecha_sitio': site_date,
        'conteos': {'propias': len(plan.own), 'terceros': len(plan.third)},
        'totales': plan.totals, 'decisiones': plan.decisions,
        'incidencias': [i.__dict__ for i in plan.issues],
        'verificacion': verification or {},
        'poligonos_pendientes': sum(r.values.get('poligonos') == 'SI' for r in plan.own + plan.third),
    }
    (base.with_suffix('.json')).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    with base.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['nivel', 'hoja', 'fila_excel', 'campo', 'detalle'])
        for issue in plan.issues:
            writer.writerow([issue.level, issue.sheet, issue.row, issue.field, issue.message])
        for dif in (verification or {}).get('diferencias', []):
            writer.writerow(['DIFERENCIA', dif.get('sheet'), dif.get('excel_row'), dif.get('field'), dif.get('message')])
    lines = [
        '# Informe local de trazabilidad', '', f'**Fase:** {phase}',
        '**Estado del envío:** NO ENVIADO POR EL PROGRAMA',
        f'**Fecha local:** {payload["fecha_informe"]}',
        f'**Archivo seleccionado:** `{Path(plan.file_path).name}`',
        f'**SHA-256:** `{plan.file_sha256}`', f'**Periodo:** {plan.period or "sin definir"}',
        f'**Fecha archivo:** {plan.file_date or "no indicada"}',
        f'**Fecha efectiva del sitio:** {site_date or "no observada"}', '',
        '| Hoja | Filas | TM originales | Original redondeado al final | TM tras redondear cada fila | Diferencia |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for label, key in [('Plantaciones Propias', 'propias'), ('Plantaciones de Terceros', 'terceros')]:
        info = plan.totals.get(key, {})
        lines.append(f'| {label} | {info.get("registros", 0)} | {info.get("tm_original", 0)} | {info.get("tm_original_redondeada_al_final", 0)} | {info.get("tm_normalizada", 0)} | {info.get("diferencia", 0)} |')
    lines += ['', f'**Polígonos pendientes:** {payload["poligonos_pendientes"]}',
              f'**Bloqueos:** {len(plan.blockers)}',
              f'**Avisos:** {len(plan.issues)-len(plan.blockers)}',
              '', '## Decisiones humanas']
    lines += ['- ' + x for x in plan.decisions] or ['- Ninguna.']
    lines += ['', '## Incidencias']
    lines += [f'- {i.level} · {i.sheet} · fila {i.row} · {i.field}: {i.message}' for i in plan.issues] or ['- Ninguna.']
    if verification:
        lines += ['', '## Verificación del formulario',
                  f'- Campos conformes: {verification.get("conformes", 0)}',
                  f'- Diferencias: {len(verification.get("diferencias", []))}']
        lines += [f'- **Automático pendiente:** {item}' for item in verification.get('automaticos_pendientes', [])]
        lines += [f'- **Aviso del sitio:** {item}' for item in verification.get('avisos_sitio', [])]
        for d in verification.get('diferencias', []):
            lines.append(f'- **Diferencia:** {d}')
    lines += ['', 'El informe **no acredita recepción, guardado o envío** al tercero.\n']
    base.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8')
    return base.with_suffix('.md')
