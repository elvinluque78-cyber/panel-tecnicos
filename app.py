from flask import Flask, request, render_template_string, redirect, url_for, session
import psycopg2
import os
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_super_secreta_panel_tecnicos_2025")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# Configuración de técnicos
TECNICOS_VALIDOS = {
    "Franyer": {"password": "franyer123", "nombre_completo": "Franyer Pérez"},
    "Wilfredo": {"password": "wilfredo123", "nombre_completo": "Wilfredo Gómez"},
    "Elvin": {"password": "elvin123", "nombre_completo": "Elvin Luque"},
    "Santiago": {"password": "santiago123", "nombre_completo": "Santiago Rodríguez"}
}

def calcular_comision(presupuesto):
    """Comisión solo para entregados: <50=5, >=60=10"""
    if presupuesto is None:
        return 0
    if presupuesto < 50:
        return 5
    elif presupuesto >= 60:
        return 10
    else:
        return 0  # Entre 50 y 59.99 no tiene comisión

def requiere_autenticacion_tecnico(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'tecnico_nombre' not in session:
            return redirect(url_for('login_tecnico'))
        return f(*args, **kwargs)
    return decorador

# HTML Login
LOGIN_TECNICO = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel Técnicos - Login</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .login-container { background: white; padding: 45px; border-radius: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); width: 380px; text-align: center; }
        h1 { color: #1a1a2e; margin-bottom: 30px; font-size: 32px; }
        input { width: 100%; padding: 14px; margin: 12px 0; border: 2px solid #e0e0e0; border-radius: 50px; font-size: 16px; transition: 0.3s; }
        input:focus { outline: none; border-color: #667eea; }
        button { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 50px; cursor: pointer; font-size: 16px; font-weight: bold; transition: 0.3s; }
        button:hover { transform: scale(1.02); }
        .error { color: #e74c3c; margin-top: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔧 Panel Técnicos</h1>
        <form method="POST">
            <input type="text" name="tecnico" placeholder="Nombre del técnico" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">Ingresar</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
'''

# HTML Dashboard (solo entregados, diseño moderno)
DASHBOARD_TECNICO = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel - {{ tecnico_nombre }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .header h1 { font-size: 28px; margin: 0; }
        .header p { font-size: 14px; opacity: 0.9; margin-top: 5px; }
        .logout { float: right; background: #e74c3c; color: white; padding: 10px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; transition: 0.3s; }
        .logout:hover { background: #c0392b; transform: scale(1.02); }
        .container { max-width: 1400px; margin: 30px auto; padding: 0 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-bottom: 40px; }
        .card { background: white; border-radius: 20px; padding: 30px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.05); transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .card h3 { color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; }
        .card .number { font-size: 52px; font-weight: bold; color: #667eea; margin: 10px 0; }
        .card .comision { font-size: 36px; font-weight: bold; color: #4caf50; }
        .seccion { background: white; border-radius: 20px; padding: 25px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
        .seccion h2 { color: #1a1a2e; margin-bottom: 20px; font-size: 22px; border-left: 4px solid #667eea; padding-left: 15px; }
        .tabla-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { border: 1px solid #e0e0e0; padding: 12px 10px; text-align: left; }
        th { background: linear-gradient(135deg, #667eea, #764ba2); color: white; font-weight: bold; }
        tr:nth-child(even) { background: #f8f9fa; }
        tr:hover { background: #f1f1f1; }
        .comision-cell { color: #4caf50; font-weight: bold; }
        .fecha { font-size: 12px; color: #666; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        @media (max-width: 768px) {
            .stats { grid-template-columns: 1fr; }
            th, td { font-size: 11px; padding: 8px 5px; }
            .header h1 { font-size: 20px; }
            .card .number { font-size: 36px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 Panel de Control - {{ tecnico_nombre }}</h1>
        <p>Elvin Technology - Equipos Entregados</p>
        <a href="/logout" class="logout">Cerrar Sesión</a>
    </div>
    <div class="container">
        <div class="stats">
            <div class="card">
                <h3>📋 Equipos Entregados</h3>
                <div class="number">{{ total_entregados }}</div>
            </div>
            <div class="card">
                <h3>💰 Comisión Total</h3>
                <div class="comision">${{ comision_total }}</div>
            </div>
        </div>
        
        <div class="seccion">
            <h2>📋 Historial de Equipos Entregados</h2>
            <div class="tabla-container">
                <table>
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Cliente</th>
                            <th>Equipo</th>
                            <th>Marca</th>
                            <th>Presupuesto</th>
                            <th>Comisión</th>
                            <th>Fecha Entrega</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for t in tickets %}
                        <tr>
                            <td>{{ t[0] }}</a></td>
                            <td>{{ t[1] }}</a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></td>
                            <table><td>{{ t[2] }}</a></td>
                            <tr><td>{{ t[3] if t[3] else '-' }}</a></td>
                            <td>${{ "%.2f"|format(t[4]) if t[4] else 0 }}</a></td>
                            <td class="comision-cell">${{ t[5] }}</a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></a></td>
                            <td class="fecha">{{ t[6][:10] if t[6] else '-' }}</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% if not tickets %}
            <p style="text-align: center; color: #666; padding: 40px;">No hay equipos entregados aún.</p>
            {% endif %}
        </div>
        
        <div class="seccion">
            <h2>💰 Tarifas de Comisión</h2>
            <div class="tabla-container">
                <table>
                    <thead>
                        <tr><th>Presupuesto</th><th>Comisión</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Menos de $50</td><td>$5</td></tr>
                        <tr><td>$60 o más</td><td>$10</td></tr>
                        <tr style="background: #f8f9fa;"><td>Entre $50 y $59.99</td><td>$0</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Elvin Technology - Sistema de Gestión de Taller</p>
        </div>
    </div>
</body>
</html>
'''

@app.route("/login_tecnico", methods=["GET", "POST"])
def login_tecnico():
    if request.method == "POST":
        tecnico = request.form.get("tecnico")
        password = request.form.get("password")
        
        if tecnico in TECNICOS_VALIDOS and TECNICOS_VALIDOS[tecnico]["password"] == password:
            session['tecnico_nombre'] = tecnico
            session['tecnico_nombre_completo'] = TECNICOS_VALIDOS[tecnico]["nombre_completo"]
            return redirect(url_for('panel_tecnico'))
        else:
            return render_template_string(LOGIN_TECNICO, error="❌ Técnico o contraseña incorrectos")
    
    return render_template_string(LOGIN_TECNICO, error=None)

@app.route("/panel")
@requiere_autenticacion_tecnico
def panel_tecnico():
    tecnico = session['tecnico_nombre']
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener SOLO tickets ENTREGADOS de este técnico
    cursor.execute('''
        SELECT codigo, cliente_nombre, equipo, marca, presupuesto, fecha_salida
        FROM reparaciones 
        WHERE tecnico = %s AND estado = 'entregado'
        ORDER BY fecha_salida DESC
    ''', (tecnico,))
    tickets_raw = cursor.fetchall()
    
    # Calcular comisión por cada ticket entregado
    tickets = []
    comision_total = 0
    for t in tickets_raw:
        comision = calcular_comision(t[4])  # presupuesto es t[4]
        comision_total += comision
        tickets.append((t[0], t[1], t[2], t[3], t[4], comision, t[5]))
    
    total_entregados = len(tickets)
    
    conn.close()
    
    return render_template_string(DASHBOARD_TECNICO, 
                                   tecnico_nombre=session['tecnico_nombre_completo'],
                                   tickets=tickets,
                                   total_entregados=total_entregados,
                                   comision_total=comision_total)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_tecnico'))

@app.route("/")
def index():
    return redirect(url_for('login_tecnico'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
