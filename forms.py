from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError
from models import Usuario

class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[
        DataRequired(message="El nombre es obligatorio."),
        Length(min=2, max=50, message="El nombre debe tener entre 2 y 50 caracteres."),
        Regexp(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', message="El nombre solo puede contener letras y espacios.")
    ])
    
    codigo_pais = SelectField('Código de país', validators=[
        DataRequired(message="Debes seleccionar un país.")
    ], choices=[])
    
    telefono = StringField('Teléfono', validators=[
        DataRequired(message="El número de teléfono es obligatorio."),
        Regexp(r'^\d+$', message="El teléfono solo puede contener números."),
        Length(min=8, max=15, message="El teléfono debe tener entre 8 y 15 dígitos.")
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message="El correo electrónico es obligatorio."),
        Email(message="El correo electrónico no es válido."),
        Length(max=100, message="El correo no puede exceder los 100 caracteres.")
    ])
    
    password = PasswordField('Contraseña', validators=[
        DataRequired(message="La contraseña es obligatoria."),
        Length(min=8, max=50, message="La contraseña debe tener entre 8 y 50 caracteres."),
        Regexp(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
               message="La contraseña debe contener al menos una mayúscula, una minúscula y un número.")
    ])

    def validate_email(self, field):
        if Usuario.query.filter_by(email=field.data).first():
            raise ValidationError('Este correo electrónico ya está registrado.')