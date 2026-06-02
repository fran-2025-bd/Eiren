"""
Conexión a Google Sheets via Service Account.
Se activa cuando se configure GOOGLE_SHEET_ID y credentials.json.
"""
import gspread
from google.oauth2.service_account import Credentials
from flask import current_app

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
]

_client = None

def get_client():
    global _client
    if _client is None:
        creds_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client

def get_sheet(nombre_hoja: str):
    client = get_client()
    sheet_id = current_app.config['GOOGLE_SHEET_ID']
    return client.open_by_key(sheet_id).worksheet(nombre_hoja)

def append_row(nombre_hoja: str, fila: list):
    get_sheet(nombre_hoja).append_row(fila, value_input_option='USER_ENTERED')

def leer_hoja(nombre_hoja: str) -> list:
    return get_sheet(nombre_hoja).get_all_records()

def registrar_clase_proxima(curso_id, nombre_curso, fecha, hora, alumnos: list):
    from datetime import datetime
    ts = datetime.utcnow().isoformat()
    for a in alumnos:
        append_row('clases_proximas', [ts, curso_id, nombre_curso, fecha, hora,
                                       a['id'], a['nombre'], a['telefono'], 'pendiente'])

def registrar_cuota_vencida(alumno_id, nombre, telefono, curso, periodo):
    from datetime import datetime
    append_row('cuotas_vencidas', [datetime.utcnow().isoformat(),
                                   alumno_id, nombre, telefono, curso, periodo, 'pendiente'])
