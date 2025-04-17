from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import Config
from routes import client_bp, auth_bp
from models import db, Usuario, Pago, Reservacion, Horario, Cancha, Clase
from functools import wraps
from datetime import datetime


# Inicializar la aplicación Flask
app = Flask(__name__)
application = app

# Añade este filtro personalizado
@app.template_filter('format_hora')
def format_hora(hora_str):
    try:
        hora = datetime.strptime(hora_str, '%H:%M:%S').time()
        return hora.strftime('%I:%M %p').lstrip('0').lower()
    except:
        return hora_str

@app.template_filter('format_time_12h')
def format_time_12h(hora_str):
    try:
        hora = datetime.strptime(hora_str, '%H:%M:%S').time()
        return hora.strftime('%I:%M %p').lstrip('0').lower()
    except:
        return hora_str

@app.template_filter('format_date')
def format_date(date_str, format='%Y-%m-%d'):
    try:
        if isinstance(date_str, str):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date_obj = date_str
        return date_obj.strftime(format)
    except:
        return date_str

app.config.from_object(Config)

# Inicializar la instancia de SQLAlchemy
db.init_app(app)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "client.login"  # Ruta a la que se redirige si no está autenticado

# Registrar los blueprints
app.register_blueprint(client_bp)  # Registrar las rutas del cliente
app.register_blueprint(auth_bp, url_prefix='/auth')  # Registrar las rutas de autenticación, prefijadas con '/auth'

# Función de carga del usuario (Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

if __name__ == "__main__":
    app.run(debug=True)
