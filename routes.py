from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models import db, Cancha, Horario, Reservacion, Usuario, Pago
from datetime import datetime, time, timedelta
import pytz
from flask_login import login_required, login_user, logout_user, current_user
import os
from werkzeug.utils import secure_filename

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
                    if usuario.role == 'admin':
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
        # Definir el rango de tiempo de 8:00 AM a 10:00 PM
        start_hour = 8  # 8:00 AM
        end_hour = 23  # 10:00 PM
        
        # Obtener la fecha actual en la zona horaria de Venezuela
        vzla_tz = pytz.timezone('America/Caracas')
        now_vzla = datetime.now(vzla_tz)
        fecha_actual = now_vzla.strftime('%Y-%m-%d')

        # Obtener todas las canchas
        canchas = Cancha.query.all()
        canchas_con_horarios = []

        # Para cada cancha, generar los horarios dentro del rango de tiempo
        for cancha in canchas:
            horarios_disponibles = []

            for hour in range(start_hour, end_hour):
                # Generar un horario para cada hora en el rango
                start_time = time(hour, 0, 0)  # Inicia en la hora completa
                end_time = time(hour + 1, 0, 0)  # El horario termina 1 hora después

                # Verificar si ya existe un horario para esa cancha y fecha
                horario_existente = Horario.query.filter_by(
                    cancha_id=cancha.id,
                    date=fecha_actual,
                    start_time=start_time
                ).first()

                # Si no existe, se crea un nuevo horario disponible
                if not horario_existente:
                    horario = Horario(
                        cancha_id=cancha.id,
                        date=fecha_actual,
                        start_time=start_time,
                        end_time=end_time,
                        estado='disponible'
                    )
                    db.session.add(horario)
                    db.session.commit()
                    horarios_disponibles.append(horario)
                elif horario_existente.estado == 'disponible':
                    horarios_disponibles.append(horario_existente)

            # Añadir la cancha y sus horarios disponibles a la lista
            canchas_con_horarios.append({
                'cancha': cancha,
                'horarios': horarios_disponibles
            })

        print(canchas_con_horarios)  # Para depuración, muestra los horarios

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


# Ruta para mis reservas
@client_bp.route('/mis_reservas')
@login_required
def mis_reservas():
    reservas = Reservacion.query.filter_by(user_id=current_user.id).all()

    formatted_reservas = []
    for reserva in reservas:
        formatted_reservas.append({
            'id': reserva.id,
            'cancha_name': reserva.horario.cancha.name,
            'fecha_reserva': reserva.horario.date.strftime('%Y-%m-%d'),
            'start_time': format_time(reserva.horario.start_time),
            'end_time': format_time(reserva.horario.end_time)
        })

    return render_template('client/mis_reservas.html', reservas=formatted_reservas)


# Ruta para la reserva de cancha
@client_bp.route('/reservar')
@login_required
def reservar():
    cancha_id = request.args.get('cancha')
    fecha = request.args.get('fecha', get_current_date().strftime('%Y-%m-%d'))
    hora = request.args.get('hora')

    if not cancha_id:
        return redirect(url_for('client.principal'))

    try:
        cancha = Cancha.query.get_or_404(cancha_id)

        horarios = Horario.query.filter_by(
            cancha_id=cancha_id,
            date=fecha,
            estado='disponible'
        ).order_by(Horario.start_time).all()

        formatted_horarios = []
        for horario in horarios:
            formatted_horarios.append({
                'start_time': horario.start_time.strftime('%H:%M:%S'),
                'formatted_time': format_time(horario.start_time)
            })

        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        fecha_error = ""
        if fecha_obj < get_current_date():
            fecha_error = "No se pueden seleccionar fechas anteriores al día actual."

        horas_seleccionadas = [hora] if hora else []

        monto_total = len(horas_seleccionadas) * float(cancha.price_per_hour)

        return render_template('client/reservar.html',
                               cancha=cancha,
                               fecha_seleccionada=fecha,
                               horas_seleccionadas=horas_seleccionadas,
                               horarios=formatted_horarios,
                               error_fecha=fecha_error,
                               monto_total=monto_total,
                               fecha_actual=get_current_date().strftime('%Y-%m-%d'))

    except Exception as e:
        return render_template('client/reservar.html', error=str(e))


@client_bp.route('/metodospago')
@login_required
def metodospago():
    cancha_id = request.args.get('cancha')
    fecha = request.args.get('fecha')
    horarios = request.args.get('horarios', '').split(',')
    monto_total = request.args.get('montoTotal')

    if not all([cancha_id, fecha, horarios, monto_total]):
        return redirect(url_for('client.principal'))

    try:
        cancha = Cancha.query.get_or_404(cancha_id)

        horarios_formateados = []
        for hora in horarios:
            if not hora:
                continue

            hora_inicio = datetime.strptime(hora, '%H:%M:%S').time()
            hora_fin = (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()

            horarios_formateados.append({
                'inicio': format_time(hora_inicio),
                'fin': format_time(hora_fin)
            })

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
        return render_template('client/metodospago.html', error=str(e))


@client_bp.route('/procesar_reserva', methods=['POST'])
@login_required
def procesar_reserva():
    try:
        cancha_id = request.form.get('cancha_id')
        fecha = request.form.get('fecha')
        horarios = request.form.get('horarios').split(',')
        metodo_pago = request.form.get('metodo_pago')
        monto_total = float(request.form.get('monto_total'))

        comprobante = None
        if 'comprobante' in request.files:
            file = request.files['comprobante']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                comprobante = filename

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

        for hora in horarios:
            if not hora:
                continue

            hora_inicio = datetime.strptime(hora, '%H:%M:%S').time()
            hora_fin = (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()

            horario = Horario(
                cancha_id=cancha_id,
                date=datetime.strptime(fecha, '%Y-%m-%d').date(),
                start_time=hora_inicio,
                end_time=hora_fin,
                estado='ocupado'
            )
            db.session.add(horario)
            db.session.flush()

            reservacion = Reservacion(
                user_id=current_user.id,
                horario_id=horario.id,
                pago_id=pago.id,
                status='pendiente'
            )
            db.session.add(reservacion)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Reserva realizada con éxito',
            'redirect': url_for('client.principal')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@client_bp.route('/perfil')
@login_required
def perfil():
    return render_template('client/perfil.html')
