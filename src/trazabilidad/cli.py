"""CLI: validar, cargar, reanudar y generar plantilla."""
import argparse
import json
import sys
from pathlib import Path
from .config import load_config
from .excel_reader import read_plan
from .report import write_report
from .template import create_template
from .browser import load_in_browser


def select_excel():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        name = filedialog.askopenfilename(title='Seleccionar plantilla de trazabilidad',
                                          filetypes=[('Excel .xlsx', '*.xlsx')])
        root.destroy()
        return name
    except Exception as exc:
        raise ValueError('No se pudo abrir el selector. Usa --file "ruta\\archivo.xlsx".') from exc


def marker_path(config):
    return config.report_dir / 'validacion_aprobada.json'


def run(argv=None):
    parser = argparse.ArgumentParser(description='Cargador local de trazabilidad · SIN ENVÍO AUTOMÁTICO')
    parser.add_argument('--config', type=Path, help='Ruta local config.local.toml')
    parser.add_argument('--url', help='URL privada: puede quedar en el historial de la terminal.')
    sub = parser.add_subparsers(dest='command', required=True)
    for action in ('validar', 'cargar', 'reanudar'):
        sp = sub.add_parser(action)
        sp.add_argument('--file', type=Path, help='Excel .xlsx; sin opción abre selector')
    tmpl = sub.add_parser('plantilla')
    tmpl.add_argument('--output', type=Path, required=True)
    tmpl.add_argument('--ejemplo-ficticio', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, args.url)
        if args.command == 'plantilla':
            print(f'Plantilla creada: {create_template(args.output, args.ejemplo_ficticio)}')
            return 0
        chosen = args.file or select_excel()
        if not chosen:
            print('No se seleccionó Excel.')
            return 2
        plan = read_plan(chosen, config)
        print(f'Periodo: {plan.period}; propias: {len(plan.own)}; terceros: {len(plan.third)}')
        for key, total in plan.totals.items():
            print(f'  {key}: {total["tm_original"]} TM originales; {total["tm_normalizada"]} TM normalizadas; diferencia={total["diferencia"]}')
        # Mostrar primero los bloqueos: los avisos repetidos pueden ocultarlos en cmd.
        blockers = plan.blockers
        warnings = [i for i in plan.issues if i.level != 'ERROR']
        print(f'Incidencias: {len(blockers)} bloqueos (ERROR); {len(warnings)} avisos (AVISO).')
        if blockers:
            print('\n========== ERRORES QUE DEBES CORREGIR ==========')
            for issue in blockers:
                print(f'ERROR {issue.sheet} fila {issue.row} campo {issue.field}: {issue.message}')
            print('================================================\n')
        if warnings:
            print('Los avisos no bloqueantes se detallan en el informe; no es necesario corregirlos todos.')
        if args.command == 'validar':
            report = write_report(plan, config.report_dir)
            print('Informe:', report)
            if plan.blockers:
                print(f'VALIDACIÓN NO APROBADA: {len(plan.blockers)} bloqueos. Navegador NO abierto.')
                return 2
            config.report_dir.mkdir(parents=True, exist_ok=True)
            marker_path(config).write_text(json.dumps({'sha256': plan.file_sha256, 'file_path': plan.file_path}), encoding='utf-8')
            print('VALIDACIÓN APROBADA, sin abrir navegador ni transmitir datos.')
            return 0
        if plan.blockers:
            print('No se puede cargar: primero resolver problemas del Excel.')
            return 2
        path = marker_path(config)
        if not path.exists() or json.loads(path.read_text(encoding='utf-8')) != {'sha256': plan.file_sha256, 'file_path': plan.file_path}:
            print('Antes de cargar, ejecute VALIDAR sobre este archivo exacto. Sin datos transmitidos.')
            return 2
        if not config.url:
            print('Configure la URL en config.local.toml. No se abre el navegador.')
            return 2
        print('\nADVERTENCIA: al abrir y completar el formulario, el sitio tercero puede recibir')
        print('datos ANTES de pulsar Enviar. El programa nunca enviará el formulario.')
        print('La página también puede realizar consultas de ubicación por su cuenta.')
        if input('Escriba exactamente CARGAR para autorizar la entrada de datos: ').strip() != 'CARGAR':
            print('Operación cancelada.')
            return 2
        state = load_in_browser(plan, config, resume=(args.command == 'reanudar'))
        return 0 if state == 'DATOS CARGADOS Y VERIFICADOS - PENDIENTE DE ENVÍO MANUAL' else 2
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
