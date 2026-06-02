from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class AlumnoForm(FlaskForm):
    """Formulario para crear y editar alumno."""

    # Datos de acceso
    username    = StringField('Usuario',
                      validators=[DataRequired(message='Requerido'),
                                   Length(min=3, max=80)])
    nombre      = StringField('Nombre completo',
                      validators=[DataRequired(message='Requerido'),
                                   Length(max=120)])
    password    = PasswordField('Contraseña',
                      validators=[Optional(), Length(min=4, message='Mínimo 4 caracteres')])

    # Datos personales
    dni                 = StringField('DNI',             validators=[Optional(), Length(max=20)])
    telefono            = StringField('Teléfono',        validators=[Optional(), Length(max=30)])
    fecha_nacimiento    = DateField('Fecha de nacimiento', validators=[Optional()])
    direccion           = StringField('Dirección',       validators=[Optional(), Length(max=200)])
    email_contacto      = StringField('Email de contacto', validators=[Optional(), Length(max=150)])

    # Contacto de emergencia
    emergencia_nombre   = StringField('Nombre contacto emergencia', validators=[Optional(), Length(max=120)])
    emergencia_telefono = StringField('Teléfono emergencia',        validators=[Optional(), Length(max=30)])

    # Notas internas
    notas   = TextAreaField('Notas internas', validators=[Optional()])
    submit  = SubmitField('Guardar')
