from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

DATA_FILE = 'data.json'

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {
            "config": {
                "whatsapp_phone": "541161772239",
                "precio_km_extra": 1500,
                "limite_km_base": 20,
                "operadora_precio": 80000,
                "calendar_id": "gonzalezdelvallesantiago@gmail.com"
            },
            "equipos": []
        }
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_datos(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    data = cargar_datos()
    # Filtramos para mostrar en el sitio web principal únicamente los equipos activos
    equipos_activos = [eq for eq in data['equipos'] if eq.get('activo', True)]
    return render_template('index.html', equipos=equipos_activos, config=data['config'])

@app.route('/admin')
def admin():
    data = cargar_datos()
    # En el panel de administración se muestran todos (activos e inactivos) para poder gestionarlos
    return render_template('admin.html', equipos=data['equipos'], config=data['config'])

@app.route('/admin/actualizar', methods=['POST'])
def actualizar_config():
    data = cargar_datos()
    
    # 1. Actualizar configuración general y costos
    data['config']['whatsapp_phone'] = request.form.get('whatsapp_phone')
    data['config']['precio_km_extra'] = float(request.form.get('precio_km_extra', 0))
    data['config']['limite_km_base'] = float(request.form.get('limite_km_base', 0))
    data['config']['operadora_precio'] = float(request.form.get('operadora_precio', 0))
    data['config']['calendar_id'] = request.form.get('calendar_id')
    
    # 2. Actualizar cada equipo dinámicamente según su ID
    for eq in data['equipos']:
        eq_id = eq['id']
        eq['nombre'] = request.form.get(f'nombre_{eq_id}')
        eq['descripcion'] = request.form.get(f'descripcion_{eq_id}')
        eq['precio_medio_dia'] = float(request.form.get(f'precio_medio_{eq_id}', 0))
        eq['precio_dia_completo'] = float(request.form.get(f'precio_completo_{eq_id}', 0))
        # El checkbox de Bootstrap envía 'on' si está tildado, de lo contrario no viaja (false)
        eq['activo'] = True if request.form.get(f'activo_{eq_id}') == 'on' else False
        
    guardar_datos(data)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)