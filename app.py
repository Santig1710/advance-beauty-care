import os
import json
from flask import Flask, render_template, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_calendar_service():
    try:
        # 1. Si estamos en Render y existe la variable de entorno con el JSON
        if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
            creds_info = json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES)
            return build('calendar', 'v3', credentials=creds)
        
        # 2. Si estamos en local y existe el archivo credentials.json
        elif os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return build('calendar', 'v3', credentials=creds)
            
        return None
    except Exception as e:
        print(f"Error al conectar con Google Calendar: {e}")
        return None

def load_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando data.json: {e}")
        return {}

@app.route('/')
def index():
    data = load_data()
    config = data.get('config', {})
    equipos = data.get('equipos', [])
    return render_template('index.html', config=config, equipos=equipos)

# Endpoint para consultar turnos ocupados
@app.route('/api/availability', methods=['GET'])
def check_availability():
    date_str = request.args.get('date')  # Formato YYYY-MM-DD
    equipo_id = request.args.get('equipo_id')
    
    if not date_str or not equipo_id:
        return jsonify({'error': 'Faltan parámetros'}), 400

    service = get_calendar_service()
    if not service:
        return jsonify({'busy_slots': []})

    data = load_data()
    calendar_id = data.get('config', {}).get('calendar_id')

    if not calendar_id:
        return jsonify({'busy_slots': []})

    time_min = f"{date_str}T00:00:00Z"
    time_max = f"{date_str}T23:59:59Z"

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        busy_slots = []

        nombre_equipo = ""
        for eq in data.get('equipos', []):
            if eq['id'] == equipo_id:
                nombre_equipo = eq['nombre'].upper()
                break

        for event in events:
            summary = event.get('summary', '').upper()
            if nombre_equipo and nombre_equipo in summary:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                busy_slots.append({'start': start, 'end': end, 'summary': summary})

        return jsonify({'busy_slots': busy_slots})
    except Exception as e:
        print(f"Error consultando eventos: {e}")
        return jsonify({'busy_slots': []})

# Endpoint para registrar la reserva en Google Calendar
@app.route('/api/book', methods=['POST'])
def create_booking():
    req_data = request.json or {}
    date_str = req_data.get('date')
    shift = req_data.get('shift')  # 'manana', 'tarde' o 'completa'
    nombre_equipo = req_data.get('nombre_equipo', 'Equipo')
    nombre_estetica = req_data.get('nombre_estetica', 'Estética')

    service = get_calendar_service()
    data = load_data()
    calendar_id = data.get('config', {}).get('calendar_id')

    if not service or not calendar_id:
        return jsonify({'error': 'Servicio de calendario no disponible'}), 500

    if shift == 'manana':
        start_time = f"{date_str}T08:00:00-03:00"
        end_time = f"{date_str}T12:00:00-03:00"
    elif shift == 'tarde':
        start_time = f"{date_str}T13:00:00-03:00"
        end_time = f"{date_str}T17:00:00-03:00"
    else:
        start_time = f"{date_str}T08:00:00-03:00"
        end_time = f"{date_str}T16:00:00-03:00"

    event = {
        'summary': f"RESERVA: {nombre_equipo} - {nombre_estetica}",
        'description': f"Reserva realizada vía web Advance Beauty Care.",
        'start': {'dateTime': start_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
        'end': {'dateTime': end_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
    }

    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return jsonify({'status': 'success', 'event_id': created_event.get('id')})
    except Exception as e:
        print(f"Error al crear evento: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)