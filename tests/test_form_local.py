"""Nunca usa la URL ni el servidor del tercero: solo HTML local ficticio."""
from pathlib import Path
from html import escape
from types import SimpleNamespace
import shutil
import pytest
from playwright.sync_api import sync_playwright
from trazabilidad.config import Config
from trazabilidad.excel_reader import read_plan
from trazabilidad.checkpoint import Checkpoints
from trazabilidad.form_adapter import FormAdapter, FormMismatch
from test_excel import basic

FIXTURE = (Path(__file__).parent/'fixtures'/'formulario_simulado.html').resolve()

def open_simulator(page):
    form = FIXTURE.read_text(encoding='utf-8')
    inner = f'<iframe id="userHtmlFrame" srcdoc="{escape(form,quote=True)}"></iframe>'
    outer = f'<iframe id="sandboxFrame" srcdoc="{escape(inner,quote=True)}"></iframe>'
    page.set_content(outer)


def _local_browser(playwright):
    kwargs={'headless':True}
    if shutil.which('chromium'):
        kwargs['executable_path'] = shutil.which('chromium')
    try:
        return playwright.chromium.launch(**kwargs)
    except Exception as exc:
        pytest.skip(f'No hay navegador disponible para la prueba local: {exc}')


@pytest.mark.browser
def test_fill_all_tabs_no_submission(tmp_path):
    xlsx=tmp_path/'solo ficticio.xlsx';basic(xlsx,3,5)
    config=Config(control_timeout_ms=5000,automatic_timeout_ms=1000,report_dir=tmp_path/'reports')
    plan=read_plan(xlsx,config)
    assert not plan.blockers
    with sync_playwright() as p:
        browser=_local_browser(p)
        page=browser.new_page()
        open_simulator(page)
        adapter=FormAdapter(page,config)
        checkpoint=Checkpoints(config.report_dir,plan.file_sha256)
        adapter.preflight(plan,checkpoint)
        adapter.load_panel(plan,checkpoint)
        adapter.load_plants('Plantaciones Propias',plan.own,checkpoint)
        adapter.load_plants('Plantaciones de Terceros',plan.third,checkpoint)
        status=adapter.verify_all(plan)
        assert not status['diferencias'], status['diferencias']
        assert not status['automaticos_pendientes'], status['automaticos_pendientes']
        assert status['conformes'] > 100
        assert adapter._rows('Panel Principal').count()==1
        assert page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame').locator('#table-PlantacionesPropias tbody tr').count()==3
        assert page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame').locator('#table-PlantacionesdeTerceros tbody tr').count()==5
        assert page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame').locator('body').evaluate('(e)=>e.ownerDocument.defaultView.submitCounter')==0
        browser.close()


@pytest.mark.browser
def test_existing_data_preflight_stops_before_writing(tmp_path):
    xlsx=tmp_path/'fake.xlsx';basic(xlsx,1,1)
    config=Config(control_timeout_ms=5000,automatic_timeout_ms=1000,report_dir=tmp_path/'reports')
    plan=read_plan(xlsx,config)
    with sync_playwright() as p:
        browser=_local_browser(p);page=browser.new_page();open_simulator(page)
        frame=page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame')
        # Datos preexistentes en TERCEROS: evita que se escriba Panel Principal.
        frame.get_by_role('button', name='Plantaciones de Terceros').click()
        frame.locator('#table-PlantacionesdeTerceros input[data-field="plantacion"]').fill('VALOR AJENO')
        adapter=FormAdapter(page,config)
        cp=Checkpoints(config.report_dir,plan.file_sha256)
        with pytest.raises(FormMismatch,match='preexistentes'):
            adapter.preflight(plan,cp)
        assert frame.locator('#nombre-diligenciador').input_value()==''
        assert frame.locator('body').evaluate('(e)=>e.ownerDocument.defaultView.submitCounter')==0
        browser.close()


@pytest.mark.browser
def test_resume_rebuilds_blank_dom(tmp_path):
    xlsx=tmp_path/'ficticio.xlsx';basic(xlsx,1,1)
    config=Config(control_timeout_ms=5000,automatic_timeout_ms=1000,report_dir=tmp_path/'reports')
    plan=read_plan(xlsx,config)
    cp=Checkpoints(config.report_dir,plan.file_sha256)
    with sync_playwright() as p:
        browser=_local_browser(p)
        page=browser.new_page();open_simulator(page)
        adapter=FormAdapter(page,config)
        adapter.preflight(plan,cp)
        adapter.load_panel(plan,cp)
        adapter.load_plants('Plantaciones Propias',plan.own,cp)
        adapter.load_plants('Plantaciones de Terceros',plan.third,cp)
        open_simulator(page)
        adapter=FormAdapter(page,config)
        adapter.preflight(plan,cp,resume=True)
        adapter.load_panel(plan,cp,resume=True)
        adapter.load_plants('Plantaciones Propias',plan.own,cp,resume=True)
        adapter.load_plants('Plantaciones de Terceros',plan.third,cp,resume=True)
        assert not adapter.verify_all(plan)['diferencias']
        browser.close()

@pytest.mark.browser
def test_changed_table_headers_fail_closed(tmp_path):
    xlsx=tmp_path/'fake.xlsx';basic(xlsx,1,1)
    config=Config(control_timeout_ms=5000,automatic_timeout_ms=1000,report_dir=tmp_path/'reports')
    plan=read_plan(xlsx,config)
    with sync_playwright() as p:
        browser=_local_browser(p);page=browser.new_page();open_simulator(page)
        frame=page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame')
        # Solo se altera el HTML del simulador, nunca el DOM del tercero.
        frame.locator('#table-panel-ext thead th').nth(2).evaluate('(e)=> e.textContent="COLUMNA NUEVA"')
        adapter=FormAdapter(page,config)
        cp=Checkpoints(config.report_dir,plan.file_sha256)
        with pytest.raises(FormMismatch, match='Estructura inesperada'):
            adapter.preflight(plan,cp)
        assert frame.locator('#nombre-diligenciador').input_value()==''
        browser.close()

@pytest.mark.browser
def test_thousandfold_decimal_bug_corrected_by_verified_second_strategy(tmp_path):
    xlsx=tmp_path/'fake decimal.xlsx';basic(xlsx,1,0)
    config=Config(control_timeout_ms=5000,automatic_timeout_ms=1000,report_dir=tmp_path/'reports')
    plan=read_plan(xlsx,config)
    with sync_playwright() as p:
        browser=_local_browser(p);page=browser.new_page();open_simulator(page)
        frame=page.frame_locator('#sandboxFrame').frame_locator('#userHtmlFrame')
        frame.locator('body').evaluate('(e)=>{e.ownerDocument.defaultView.simulateDecimalBug=true}')
        adapter=FormAdapter(page,config);cp=Checkpoints(config.report_dir,plan.file_sha256)
        adapter.preflight(plan,cp);adapter.load_panel(plan,cp)
        adapter.load_plants('Plantaciones Propias',plan.own,cp)
        adapter.load_plants('Plantaciones de Terceros',plan.third,cp)
        assert not adapter.verify_all(plan)['diferencias']
        assert frame.locator('#table-PlantacionesPropias [data-field="fruto_tm"]').first.input_value()=='15.58'
        assert frame.locator('body').evaluate('(e)=>e.ownerDocument.defaultView.submitCounter')==0
        browser.close()
