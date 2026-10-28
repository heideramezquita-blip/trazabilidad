"""Esquema interno. Ningún dato de producción se incluye en el repositorio."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

SHEETS = ('Panel Principal', 'Plantaciones Propias', 'Plantaciones de Terceros')
MILL_FIELDS = {
    'B': 'uml_id', 'C': 'empresa_matriz', 'D': 'empresa_molino', 'E': 'molino',
    'F': 'rspo', 'G': 'otras_certificaciones', 'H': 'latitud', 'I': 'longitud',
    'J': 'direccion', 'K': 'departamento', 'L': 'municipio', 'M': 'pais',
    'N': 'pct_propias', 'O': 'pct_terceros', 'P': 'cpo_tm', 'Q': 'pko_tm',
}
PLANT_FIELDS = {
    'B': 'tipo', 'C': 'empresa_matriz', 'D': 'plantacion', 'E': 'id_plantacion',
    'F': 'rspo', 'G': 'area_ha', 'H': 'latitud', 'I': 'longitud',
    'J': 'municipio', 'K': 'departamento', 'L': 'pais',
    'M': 'otras_certificaciones', 'N': 'anio_certificacion',
    'O': 'fruto_tm', 'P': 'pct_estimado', 'Q': 'poligonos',
}
HEADERS_MILL = {
    'A': '#', 'B': 'UML ID', 'C': 'Empresa matriz', 'D': 'Empresa del molino',
    'E': 'Nombre del Molino', 'F': 'Certificación RSPO', 'G': 'Otras certificaciones',
    'H': 'Latitud', 'I': 'Longitud', 'J': 'Dirección', 'K': 'Departamento',
    'L': 'Municipio', 'M': 'País', 'N': '% Propias', 'O': '% Terceros',
    'P': 'Volumen CPO (TM)', 'Q': 'Volumen PKO (TM)',
}
HEADERS_PLANT = {
    'A': '#', 'B': 'Tipo Plantación', 'C': 'Empresa matriz',
    'D': 'Nombre de Plantación', 'E': 'ID Plantación', 'F': 'Certificación RSPO',
    'G': 'Área Total (Ha)', 'H': 'Latitud', 'I': 'Longitud',
    'J': 'Municipio', 'K': 'Departamento', 'L': 'País',
    'M': 'Otras certificaciones', 'N': 'Año Certificación',
    'O': 'Fruto entregado (TM)', 'P': '% Estimado', 'Q': '¿Polígonos?',
}
AUTO_FIELDS = {'tipo', 'municipio', 'departamento', 'pais', 'pct_estimado'}
TEXT_FIELDS = {'uml_id', 'empresa_matriz', 'empresa_molino', 'molino', 'otras_certificaciones',
               'direccion', 'plantacion', 'id_plantacion'}
DECIMAL_FIELDS = {'latitud': 6, 'longitud': 6, 'area_ha': 2, 'cpo_tm': 2, 'pko_tm': 2, 'fruto_tm': 2}
NUMERIC_OTHER = {'pct_propias', 'pct_terceros'}
SELECT_FIELDS = {'rspo', 'poligonos'}

@dataclass
class Issue:
    level: str
    sheet: str
    row: int
    field: str
    message: str

@dataclass
class Record:
    sheet: str
    excel_row: int
    values: dict[str, str | None]
    original_tm: str | None = None

@dataclass
class Plan:
    file_path: str
    file_sha256: str
    period: str | None = None
    file_date: str | None = None
    operator: str | None = None
    mill: Record | None = None
    own: list[Record] = field(default_factory=list)
    third: list[Record] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    totals: dict[str, Any] = field(default_factory=dict)

    @property
    def blockers(self):
        return [i for i in self.issues if i.level == 'ERROR']

    def serialize(self):
        return asdict(self)
