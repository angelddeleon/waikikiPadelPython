from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Numeric, Enum
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    telefono = db.Column(db.String(15))
    password = db.Column(db.String(255), nullable=False)
    codigoPais = db.Column(db.String(10))
    role = db.Column(db.Enum('usuario', 'admin'), nullable=False)
    isBlocked = db.Column(db.Boolean, default=False)
    perfil = db.Column(db.String(255))

    def __repr__(self):
        return f"<Usuario {self.nombre} - {self.email}>"

    def set_password(self, password):
        """Generar y asignar el hash de la contraseña"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verificar si la contraseña proporcionada coincide con el hash almacenado"""
        return check_password_hash(self.password, password)

# Modelo para la tabla 'canchas'
class Cancha(db.Model):
    __tablename__ = 'canchas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    price_per_hour = db.Column(Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<Cancha {self.name} - {self.price_per_hour}>"


# Modelo para la tabla 'horarios'
class Horario(db.Model):
    __tablename__ = 'horarios'

    id = db.Column(db.Integer, primary_key=True)
    cancha_id = db.Column(db.Integer, db.ForeignKey('canchas.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    estado = db.Column(db.Enum('disponible', 'ocupado'), default='disponible')

    cancha = db.relationship('Cancha', backref=db.backref('horarios', lazy=True))

    def __repr__(self):
        return f"<Horario {self.date} - {self.start_time} to {self.end_time}>"


class Pago(db.Model):
    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.Enum('efectivo', 'pago movil', 'zelle', 'punto de venta'), nullable=False)
    payment_proof = db.Column(db.String(255))
    payment_status = db.Column(db.Enum('pendiente', 'completado', 'rechazado'), default='pendiente')
    payment_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    tasa_valor = db.Column(Numeric(10, 2), nullable=False)

    usuario = db.relationship('Usuario', backref=db.backref('pagos', lazy=True))
    # Aquí usamos 'back_populates' para establecer la relación inversa.
    reservaciones = db.relationship('Reservacion', back_populates='pago', lazy=True)

    def __repr__(self):
        return f"<Pago {self.id} - {self.amount} - {self.payment_status}>"


# Modelo para la tabla 'reservaciones'
class Reservacion(db.Model):
    __tablename__ = 'reservaciones'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    horario_id = db.Column(db.Integer, db.ForeignKey('horarios.id'), nullable=False)
    pago_id = db.Column(db.Integer, db.ForeignKey('pagos.id'), nullable=True)  # Relación muchos a uno
    status = db.Column(db.Enum('pendiente', 'confirmada', 'cancelada', 'terminada'), default='pendiente')

    usuario = db.relationship('Usuario', backref=db.backref('reservaciones', lazy=True))
    horario = db.relationship('Horario', backref=db.backref('reservaciones', lazy=True))
    pago = db.relationship('Pago', back_populates='reservaciones')

    def __repr__(self):
        return f"<Reservacion {self.id} - {self.status}>"

class Clase(db.Model):
    __tablename__ = 'clases'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    horario_id = db.Column(db.Integer, db.ForeignKey('horarios.id'), nullable=False)
    status = db.Column(db.Enum('pendiente', 'realizada', 'cancelada'), default='pendiente')

    # Relación con horario (una clase tiene un solo horario)
    horario = db.relationship('Horario', backref='clase', lazy=True)

    def __repr__(self):
        return f"<Clase {self.nombre}, Status: {self.status}>"


# Modelo para la tabla 'tasa'
class Tasa(db.Model):
    __tablename__ = 'tasa'

    id = db.Column(db.Integer, primary_key=True, default=1)
    monto = db.Column(Numeric(10, 2), nullable=False, comment='Valor de la tasa con 2 decimales')
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, comment='Fecha de última actualización')

    def __repr__(self):
        return f"<Tasa {self.monto}>"
