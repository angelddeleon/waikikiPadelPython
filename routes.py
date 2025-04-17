from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from models import db, Cancha, Horario, Reservacion, Usuario, Pago
from datetime import datetime, time, timedelta
import pytz
from flask_login import login_required, login_user, logout_user, current_user
import os
from werkzeug.utils import secure_filename
from forms import RegistroForm
import requests
from werkzeug.security import generate_password_hash  # También necesitas esta importación

# Blueprint para las rutas del cliente y autenticación
client_bp = Blueprint('client', __name__, url_prefix='/')
auth_bp = Blueprint('auth', __name__)

# Configuración para las subidas de archivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Funciones de utilidad
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_date():
    vzla_tz = pytz.timezone('America/Caracas')
    return datetime.now(vzla_tz).date()

def format_time(time_str):
    if isinstance(time_str, str):
        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
    else:
        time_obj = time_str
    return time_obj.strftime("%I:%M %p")

def obtener_horas_disponibles(cancha_id, fecha):
    try:
        vzla_timezone = pytz.timezone("America/Caracas")
        hora_actual_vzla = datetime.now(vzla_timezone).strftime("%H:%M:%S")
        dia_actual = datetime.today().date()
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()

        # Primero intentamos con la fecha solicitada
        horarios_ocupados = Horario.query.filter_by(
            cancha_id=cancha_id, 
            date=fecha_obj,
            estado='ocupado'
        ).all()
        
        horas_ocupadas = [ho.start_time.strftime('%H:%M:%S') for ho in horarios_ocupados]
        horarios_disponibles = []

        # Generar horarios de 8:00 a 23:00
        for hora in range(8, 23):
            hora_inicio = time(hour=hora, minute=0, second=0).strftime('%H:%M:%S')
            
            # Verificar disponibilidad
            if ((fecha_obj > dia_actual) or 
                (fecha_obj == dia_actual and hora_inicio > hora_actual_vzla)):
                if hora_inicio not in horas_ocupadas:
                    horario = Horario(
                        cancha_id=cancha_id,
                        date=fecha_obj,
                        start_time=time(hour=hora, minute=0, second=0),
                        end_time=time(hour=hora+1, minute=0, second=0),
                        estado='disponible'
                    )
                    horarios_disponibles.append(horario)

        # Si no hay horarios disponibles para la fecha solicitada, probamos con el día siguiente
        if not horarios_disponibles and fecha_obj == dia_actual:
            dia_siguiente = dia_actual + timedelta(days=1)
            return obtener_horas_disponibles(cancha_id, dia_siguiente.strftime('%Y-%m-%d'))

        return horarios_disponibles

    except Exception as e:
        print(f"Error al obtener horarios disponibles: {e}")
        return None

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    
    if not form.codigo_pais.choices or len(form.codigo_pais.choices) <= 1:
        try:
            response = requests.get('https://restcountries.com/v3.1/all?fields=name,idd')
            if response.status_code == 200:
                countries = response.json()
                country_list = [('', 'Selecciona tu país')]  # Opción por defecto
                
                for country in sorted(countries, key=lambda x: x['name']['common']):
                    name = country['name']['common']
                    idd = country.get('idd', {})
                    
                    if idd and idd.get('root') and idd.get('suffixes'):
                        root = idd['root'].strip()
                        suffix = idd['suffixes'][0] if idd['suffixes'] else ''
                        code = f"{root}{suffix}"
                        country_list.append((code, f"{code} - {name}"))
                
                form.codigo_pais.choices = country_list
        except Exception as e:
            current_app.logger.error(f"Error al obtener países: {str(e)}")
            # Opciones por defecto si falla la API
            form.codigo_pais.choices = [
                ('', 'Selecciona tu país'),
                ('+58', '+58 - Venezuela'),
                ('+1', '+1 - USA/Canada'),
                ('+34', '+34 - España')
            ]
            flash("Error al cargar los códigos de país. Usando lista básica.", "error")

    if form.validate_on_submit():
        try:
            nuevo_usuario = Usuario(
                nombre=form.nombre.data,
                email=form.email.data,
                telefono=form.telefono.data,
                codigoPais=form.codigo_pais.data,
                password=generate_password_hash(form.password.data),
                role='usuario',
                isBlocked=False,
                perfil='default.png'
            )
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            flash("Registro exitoso. Por favor inicia sesión.", "success")
            return redirect(url_for('client.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error en registro: {str(e)}")
            flash("Ocurrió un error al registrar. Por favor, inténtalo de nuevo.", "error")

    return render_template('auth/registro.html', form=form)

@client_bp.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('client.principal'))

    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            usuario = db.session.query(Usuario).filter_by(email=email).first()

            if usuario:
                if usuario.check_password(password):
                    if usuario.isBlocked:
                        flash('Tu cuenta está bloqueada. No puedes iniciar sesión.', 'danger')
                        return redirect(url_for('client.login'))

                    login_user(usuario)
                    flash('Inicio de sesión exitoso', 'success')
                    if usuario.role == 'usuario':
                        return redirect(url_for('client.principal'))
                    else:
                        flash('No tienes acceso de administrador', 'danger')
                        return redirect(url_for('client.login'))
                else:
                    flash('Contraseña incorrecta', 'danger')
            else:
                flash('Correo electrónico no registrado', 'danger')

    except Exception as e:
        flash('Ocurrió un error inesperado. Por favor, inténtalo de nuevo más tarde.', 'danger')

    return render_template('login.html')

@client_bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('client.login'))


@client_bp.route('/principal')
@login_required
def principal():
    try:
        # Obtener la fecha actual en la zona horaria de Venezuela
        vzla_tz = pytz.timezone('America/Caracas')
        now_vzla = datetime.now(vzla_tz)
        fecha_actual = now_vzla.strftime('%Y-%m-%d')

        # Obtener todas las canchas
        canchas = Cancha.query.all()
        canchas_con_horarios = []

        # Para cada cancha, obtener los horarios disponibles
        for cancha in canchas:
            horarios_disponibles = obtener_horas_disponibles(cancha.id, fecha_actual)

            # Si no hay horarios disponibles para la cancha, no la mostramos
            if horarios_disponibles:
                canchas_con_horarios.append({
                    'cancha': cancha,
                    'horarios': horarios_disponibles
                })

        # Obtener las reservas del usuario
        reservas = Reservacion.query.join(Horario).filter(
            Reservacion.user_id == current_user.id,
            Horario.date >= fecha_actual
        ).order_by(Horario.date, Horario.start_time).all()

        formatted_reservas = []
        for reserva in reservas:
            formatted_reservas.append({
                'id': reserva.id,
                'cancha_name': reserva.horario.cancha.name,
                'status': reserva.status,
                'fecha_reserva': reserva.horario.date.strftime('%Y-%m-%d'),
                'start_time': format_time(reserva.horario.start_time),
                'end_time': format_time(reserva.horario.end_time)
            })

        # Pasar las canchas con horarios y las reservas a la plantilla
        return render_template('client/principal.html',
                               canchas=canchas_con_horarios,
                               reservas=formatted_reservas,
                               whatsapp_number="584244520697",
                               whatsapp_message="Hola, 1.Me interesa hacer una reserva en su cancha, 2.Tuve un problema al hacer mi reserva")

    except Exception as e:
        return render_template('client/principal.html', error=str(e))

@client_bp.route('/mis_reservas', methods=['GET'])
@login_required
def mis_reservas():
    try:
        # Obtener las reservas del usuario
        reservas = Reservacion.query.join(Horario).filter(
            Reservacion.user_id == current_user.id
        ).order_by(Horario.date, Horario.start_time).all()

        # Formatear las reservas
        formatted_reservas = []
        for reserva in reservas:
            formatted_reservas.append({
                'id': reserva.id,
                'cancha_name': reserva.horario.cancha.name,
                'status': reserva.status,
                'fecha_reserva': reserva.horario.date.strftime('%Y-%m-%d'),
                'start_time': format_time(reserva.horario.start_time),
                'end_time': format_time(reserva.horario.end_time)
            })

        # Renderizar la plantilla mis_reservas.html
        return render_template('client/mis_reservas.html', reservas=formatted_reservas)

    except Exception as e:
        return render_template('client/mis_reservas.html', error=str(e))

@client_bp.route('/reservar', methods=['GET', 'POST'])
@login_required
def reservar():
    cancha_id = request.args.get('cancha')
    fecha = request.args.get('fecha', get_current_date().strftime('%Y-%m-%d'))
    hora = request.args.get('hora')

    if not cancha_id:
        flash('Debes seleccionar una cancha', 'error')
        return redirect(url_for('client.principal'))

    try:
        cancha = Cancha.query.get_or_404(cancha_id)
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        dia_actual = get_current_date()

        # Obtener horarios disponibles (puede devolver horarios del día siguiente)
        horarios_disponibles = obtener_horas_disponibles(cancha.id, fecha)

        if horarios_disponibles and horarios_disponibles[0].date != fecha_obj:
            nueva_fecha = horarios_disponibles[0].date.strftime('%Y-%m-%d')
            flash(f'No hay horarios disponibles para la fecha seleccionada. Mostrando horarios para {nueva_fecha}', 'info')
            return redirect(url_for('client.reservar', 
                                cancha=cancha.id,
                                fecha=nueva_fecha))

        # Procesar horas seleccionadas
        horas_seleccionadas = request.args.get('horas_seleccionadas', '')
        horas_seleccionadas = [h for h in horas_seleccionadas.split(',') if h]
        
        # Manejar selección/deselección de hora
        if hora:
            if hora in horas_seleccionadas:
                horas_seleccionadas.remove(hora)  # Deseleccionar si ya está seleccionada
            else:
                horas_seleccionadas.append(hora)  # Seleccionar si no está seleccionada

        # Validar fecha
        fecha_error = ""
        if fecha_obj < dia_actual:
            fecha_error = "No se pueden seleccionar fechas anteriores al día actual."
            horarios_disponibles = []

        # Calcular monto
        monto_total = len(horas_seleccionadas) * float(cancha.price_per_hour)

        # Manejar POST (selección de hora)
        if request.method == 'POST' and 'hora' in request.form:
            nueva_hora = request.form['hora']
            if nueva_hora in horas_seleccionadas:
                horas_seleccionadas.remove(nueva_hora)
            else:
                horas_seleccionadas.append(nueva_hora)
            return redirect(url_for('client.reservar',
                                cancha=cancha.id,
                                fecha=fecha,
                                horas_seleccionadas=','.join(horas_seleccionadas)))

        return render_template('client/reservar.html',
                           cancha=cancha,
                           fecha_seleccionada=fecha,
                           horas_seleccionadas=horas_seleccionadas,
                           horarios=horarios_disponibles,
                           error_fecha=fecha_error,
                           monto_total=monto_total,
                           fecha_actual=dia_actual.strftime('%Y-%m-%d'))

    except Exception as e:
        current_app.logger.error(f"Error en reservar: {str(e)}")
        flash('Ocurrió un error al cargar la página de reserva', 'error')
        return redirect(url_for('client.principal'))

@client_bp.route('/metodospago')
@login_required
def metodospago():
    try:
        cancha_id = request.args.get('cancha')
        fecha = request.args.get('fecha')
        horarios = request.args.get('horarios', '').split(',')
        monto_total = float(request.args.get('montoTotal', 0))

        if not all([cancha_id, fecha, horarios]):
            flash('Faltan parámetros necesarios para el pago', 'error')
            return redirect(url_for('client.principal'))

        cancha = Cancha.query.get_or_404(cancha_id)

        # Filtrar horarios vacíos
        horarios = [h for h in horarios if h]
        
        # Formatear horarios para mostrar (formato 12 horas)
        horarios_formateados = []
        for hora in horarios:
            hora_inicio = datetime.strptime(hora, '%H:%M:%S').time()
            hora_fin = (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()
            
            horarios_formateados.append({
                'inicio_24h': hora_inicio.strftime('%H:%M:%S'),  # Para guardar en BD
                'fin_24h': hora_fin.strftime('%H:%M:%S'),        # Para guardar en BD
                'inicio': hora_inicio.strftime('%I:%M %p').lstrip('0').lower(),  # Para mostrar
                'fin': hora_fin.strftime('%I:%M %p').lstrip('0').lower()         # Para mostrar
            })

        # Métodos de pago disponibles
        metodos_pago = {
            "Pago Móvil": {"requiere_comprobante": True},
            "Zelle": {"requiere_comprobante": True},
            "Efectivo": {"requiere_comprobante": False}
        }

        return render_template('client/metodospago.html',
                           cancha=cancha,
                           fecha=fecha,
                           horarios=horarios_formateados,
                           monto_total=monto_total,
                           metodos_pago=metodos_pago)

    except Exception as e:
        current_app.logger.error(f"Error en metodospago: {str(e)}")
        flash('Ocurrió un error al procesar el pago', 'error')
        return redirect(url_for('client.principal'))

@client_bp.route('/procesar_reserva', methods=['POST'])
@login_required
def procesar_reserva():
    try:
        # Obtener datos del formulario
        cancha_id = request.form.get('cancha_id')
        fecha = request.form.get('fecha')
        horarios = request.form.get('horarios').split(',')
        metodo_pago = request.form.get('metodo_pago')  # Asegúrate que coincida con el name del input
        monto_total = float(request.form.get('monto_total'))

        # Procesar comprobante de pago si existe
        comprobante = None
        if 'comprobante' in request.files:
            file = request.files['comprobante']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                comprobante = filename

        # Crear registro de pago
        pago = Pago(
            user_id=current_user.id,
            amount=monto_total,
            payment_method=metodo_pago.lower(),
            payment_status='pendiente',
            payment_proof=comprobante,
            payment_date=datetime.utcnow(),
            tasa_valor=1.0
        )
        db.session.add(pago)
        db.session.flush()

        # Crear horarios y reservaciones
        for hora in horarios:
            if not hora:
                continue

            hora_inicio = datetime.strptime(hora, '%H:%M:%S').time()
            hora_fin = (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()

            # Registrar horario
            horario = Horario(
                cancha_id=cancha_id,
                date=datetime.strptime(fecha, '%Y-%m-%d').date(),
                start_time=hora_inicio,
                end_time=hora_fin,
                estado='ocupado'
            )
            db.session.add(horario)
            db.session.flush()

            # Crear reservación
            reservacion = Reservacion(
                user_id=current_user.id,
                horario_id=horario.id,
                pago_id=pago.id,
                status='pendiente'
            )
            db.session.add(reservacion)

        db.session.commit()
        flash('✅ Reserva realizada con éxito', 'success')
        return redirect(url_for('client.principal'))

    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al procesar la reserva: {str(e)}', 'error')
        return redirect(request.referrer or url_for('client.principal'))

@client_bp.route('/perfil')
@login_required
def perfil():
    return render_template('client/perfil.html')

@client_bp.route('/canchas', methods=['GET'])
@login_required
def canchas():
    try:
        # Obtener todas las canchas
        canchas = Cancha.query.all()
        canchas_con_horarios = []

        # Para cada cancha, obtener los horarios disponibles
        for cancha in canchas:
            horarios_disponibles = obtener_horas_disponibles(cancha.id, get_current_date().strftime('%Y-%m-%d'))

            # Si no hay horarios disponibles para la cancha, no la mostramos
            if horarios_disponibles:
                canchas_con_horarios.append({
                    'cancha': cancha,
                    'horarios': horarios_disponibles
                })

        # Renderizar la plantilla canchas.html
        return render_template('client/canchas.html', canchas=canchas_con_horarios)

    except Exception as e:
        return render_template('client/canchas.html', error=str(e))
