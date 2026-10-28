"""Checkpoint por fila. Nunca sustituye la lectura del DOM real."""
from pathlib import Path
from hashlib import sha256
import json


def record_hash(record):
    value = json.dumps(record.values, sort_keys=True, ensure_ascii=False)
    return sha256(value.encode('utf-8')).hexdigest()


class Checkpoints:
    def __init__(self, directory, file_hash):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f'checkpoint_{file_hash}.json'
        self.file_hash = file_hash
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'excel_sha256': file_hash, 'rows': {}}
        if self.data.get('excel_sha256') != file_hash:
            raise ValueError('El checkpoint pertenece a otro archivo.')

    def _key(self, record, index):
        return f'{record.sheet}:{record.excel_row}:{index}'

    def has(self, record, index):
        item = self.data['rows'].get(self._key(record, index))
        return bool(item and item['normalized_sha256'] == record_hash(record) and item['verified'])

    def save(self, record, index):
        self.data['rows'][self._key(record, index)] = {
            'sheet': record.sheet, 'excel_row': record.excel_row,
            'web_position': index, 'normalized_sha256': record_hash(record),
            'verified': True,
        }
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)
