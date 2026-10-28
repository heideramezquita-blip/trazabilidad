"""Arranca una ventana propia de Edge/Chromium; no usa navegador del usuario."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from .form_adapter import FormAdapter, FormMismatch
from .checkpoint import Checkpoints
from .report import write_report


def load_in_browser(plan, config, resume=False):
    if not config.url:
        raise ValueError('Configura la URL privada en config.local.toml antes de cargar.')
    profile = config.profile_dir.resolve()
    if 'microsoft/edge/user data' in str(profile).replace('\\', '/').lower():
        raise ValueError('No se admite el perfil habitual de Edge; usa uno exclusivo.')
    profile.mkdir(parents=True, exist_ok=True)
    checkpoints = Checkpoints(config.report_dir, plan.file_sha256)
    pw = sync_playwright().start()
    context = None
    phase = 'CARGA PARCIAL'
    verification = None
    last_date = None
    try:
        kwargs = {'user_data_dir': str(profile), 'headless': False,
                  'accept_downloads': False, 'no_viewport': True}
        if config.browser == 'msedge':
            kwargs['channel'] = 'msedge'
        context = pw.chromium.launch_persistent_context(**kwargs)
        page = context.pages[0] if context.pages else context.new_page()
        # La navegación usa únicamente la URL que confirmó el usuario.
        page.goto(config.url, wait_until='domcontentloaded', timeout=60000)
        adapter = FormAdapter(page, config)
        adapter.preflight(plan, checkpoints, resume=resume)
        last_date = adapter.last_date
        adapter.load_panel(plan, checkpoints, resume=resume)
        adapter.load_plants('Plantaciones Propias', plan.own, checkpoints, resume=resume)
        adapter.load_plants('Plantaciones de Terceros', plan.third, checkpoints, resume=resume)
        verification = adapter.verify_all(plan)
        if verification['diferencias'] or verification['automaticos_pendientes']:
            phase = 'PENDIENTE DE REVISIÓN'
        else:
            phase = 'DATOS CARGADOS Y VERIFICADOS - PENDIENTE DE ENVÍO MANUAL'
        print(f'\nResultado: {phase}')
        print(f'Diferencias: {len(verification["diferencias"])}; automáticos pendientes: {len(verification["automaticos_pendientes"])}')
    except KeyboardInterrupt:
        print('\nInterrupción de carga. Se conservan checkpoints de filas verificadas.')
    except Exception as exc:
        # Playwright suele incluir la URL visitada en sus errores. Nunca imprimirla.
        safe_message = re.sub(r'https?://[^\s\"\'<>()]+', '[URL PRIVADA]', str(exc))
        print(f'\nCARGA DETENIDA: {type(exc).__name__}: {safe_message}')
    finally:
        report = write_report(plan, config.report_dir, phase, verification, last_date)
        print(f'Informe local: {report}')
        print('El programa NO ha pulsado «COMPLETAR Y ENVIAR».')
        if context:
            print('La ventana queda abierta. Revise y, si decide, envíe MANUALMENTE.')
            print('Cerrar o recargar puede perder datos que aún no están guardados en el sitio.')
            try:
                input('Pulse INTRO cuando quiera cerrar SOLO esta ventana del cargador... ')
            except (EOFError, KeyboardInterrupt):
                print('Consola terminada; cerrando únicamente el navegador exclusivo.')
            finally:
                context.close()
        pw.stop()
    return phase
