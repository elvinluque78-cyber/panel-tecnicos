from flask import Flask, request, render_template_string, redirect, url_for, session
import psycopg2
import os
import datetime
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_super_secreta_para_panel_tecnicos_2025")

# PostgreSQL desde variable de entorno (misma base que el taller)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# Configuración de técnicos (usuario = nombre del técnico, contraseña = puede ser personalizada)
TECNICOS_VALIDOS = {
    "Franyer": {"password": "franyer123", "nombre_completo": "Franyer Pérez"},
    "Carlos": {"password": "carlos123", "nombre_completo": "Carlos López"},
    "Luis": {"password": "luis123", "nombre_completo": "Luis Martínez"}
}

def requiere_autenticacion_tecnico(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'tecnico_nombre' not in session:
            return redirect(url_for('login_tecnico'))
        return f(*args, **kwargs)
    return decorador

# HTML Login para técnicos
LOGIN_TECNICO = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel Técnicos - Login</title>
    <style>
        body { font-family: sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; justify-content: center; align-items: center; }
        .login-container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 320px; }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #5a67d8; }
        .error { color: red; text-align: center; margin-top: 10px; }
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

# HTML Dashboard del técnico
DASHBOARD_TECNICO = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel de {{ tecnico }}</title>
    <style>
        body { font-family: sans-serif; margin: 0; background: #f0f2f5; }
        .header { background: #667eea; color: white; padding: 20px; text-align: center; }
        .container { max-width: 1200px; margin: 20px auto; padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .card h3 { margin: 0; color: #666; font-size: 14px; }
        .card .number { font-size: 36px; font-weight: bold; margin: 10px 0; color: #667eea; }
        .card .total { font-size: 24px; font-weight: bold; color: #48bb78; }
        table { width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #667eea; color: white; }
        tr:hover { background: #f5f5f5; }
        .estado-lista { color: green; font-weight: bold; }
        .estado-entregado { color: blue; font-weight: bold; }
        .logout { float: right; background: #e53e3e; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; margin-top: 10px; }
        .logout:hover { background: #c53030; }
        .btn { display: inline-block; background: #48bb78; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
        .btn:hover { background: #38a169; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 Panel de Control - {{ tecnico_nombre }}</h1>
        <a href="/logout" class="logout">Cerrar Sesión</a>
    </div>
    <div class="container">
        <div class="stats">
            <div class="card">
                <h3>📋 Total Reparaciones</h3>
                <div class="number">{{ total_reparaciones }}</div>
            </div>
            <div class="card">
                <h3>✅ Reparaciones Entregadas</h3>
                <div class="number">{{ entregadas }}</div>
            </div>
            <div class="card">
                <h3>💰 Total Facturado (entregadas)</h3>
                <div class="total">${{ total_facturado }}</div>
            </div>
            <div class="card">
                <h3>💵 Comisión Estimada (30%)</h3>
                <div class="total">${{ comision }}</div>
            </div>
        </div>
        
        <h2>📋 Mis Reparaciones</h2>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Cliente</th>
                    <th>Equipo</th>
                    <th>Estado</th>
                    <th>Presupuesto</th>
                    <th>Fecha Entrada</th>
                    <th>Fecha Entrega</th>
                </tr>
            </thead>
            <tbody>
                {% for r in reparaciones %}
                <tr>
                    <td>{{ r[0] }}</td>
                    <td>{{ r[1] }}</td>
                    <td>{{ r[2] }} {{ r[3] }}</td>
                    <td class="estado-{{ r[4] }}">{{ r[4].replace('_', ' ').upper() }}</td>
                    <td>${{ r[5] if r[5] else 0 }}</td>
                    <td>{{ r[6][:10] if r[6] else '' }}</td>
                    <td>{{ r[7][:10] if r[7] else 'Pendiente' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <a href="/exportar" class="btn">📥 Exportar a CSV</a>
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
    
    # Obtener todas las reparaciones de este técnico
    cursor.execute('''
        SELECT codigo, cliente_nombre, equipo, marca, estado, presupuesto, fecha_entrada, fecha_salida
        FROM reparaciones 
        WHERE tecnico = %s 
        ORDER BY id DESC
    ''', (tecnico,))
    reparaciones = cursor.fetchall()
    
    # Estadísticas
    cursor.execute('''
        SELECT COUNT(*) FROM reparaciones WHERE tecnico = %s
    ''', (tecnico,))
    total_reparaciones = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT COUNT(*) FROM reparaciones WHERE tecnico = %s AND estado = 'entregado'
    ''', (tecnico,))
    entregadas = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT SUM(presupuesto) FROM reparaciones WHERE tecnico = %s AND estado = 'entregado'
    ''', (tecnico,))
    total_facturado = cursor.fetchone()[0] or 0
    
    conn.close()
    
    comision = round(total_facturado * 0.30, 2)  # 30% comisión
    
    return render_template_string(DASHBOARD_TECNICO, 
                                   tecnico=tecnico,
                                   tecnico_nombre=session['tecnico_nombre_completo'],
                                   reparaciones=reparaciones,
                                   total_reparaciones=total_reparaciones,
                                   entregadas=entregadas,
                                   total_facturado=total_facturado,
                                   comision=comision)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_tecnico'))

@app.route("/exportar")
@requiere_autenticacion_tecnico
def exportar_csv():
    import csv
    from io import StringIO
    from flask import Response
    
    tecnico = session['tecnico_nombre']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT codigo, cliente_nombre, equipo, marca, falla, estado, presupuesto, fecha_entrada, fecha_salida
        FROM reparaciones 
        WHERE tecnico = %s 
        ORDER BY id DESC
    ''', (tecnico,))
    reparaciones = cursor.fetchall()
    conn.close()
    
    # Crear CSV en memoria
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Código', 'Cliente', 'Equipo', 'Marca', 'Falla', 'Estado', 'Presupuesto', 'Fecha Entrada', 'Fecha Salida'])
    
    for r in reparaciones:
        cw.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8] if r[8] else ''])
    
    output = si.getvalue()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=reparaciones_{tecnico}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.route("/")
def index():
    return redirect(url_for('login_tecnico'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
