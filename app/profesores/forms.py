from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

CONDICIONES_PAGO = [
    ('', '-- Seleccionar --'),
    ('por_cuota',   'Por cuota cobrada'),
    ('mensual',     'Mensual fijo'),
    ('por_clase',   'Por clase dictada'),
]

class ProfesorForm(FlaskForm):

    # Datos de acceso
    username = StringField('Usuario',
                 validators=[DataRequired(), Length(min=3, max=80)])
    nombre   = StringField('Nombre completo',
                 validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Contraseña',
                 validators=[Optional(), Length(min=4)])

    # Datos personales
    dni              = StringField('DNI',             validators=[Optional(), Length(max=20)])
    telefono         = StringField('Teléfono',        validators=[Optional(), Length(max=30)])
    fecha_nacimiento = DateField('Fecha de nacimiento', validators=[Optional()])
    email_contacto   = StringField('Email de contacto', validators=[Optional(), Length(max=150)])
    direccion        = StringField('Dirección',       validators=[Optional(), Length(max=200)])

    # Condición de pago
    condicion_pago = SelectField('Condición de pago',
                         choices=CONDICIONES_PAGO,
                         validators=[Optional()])

    # Notas internas
    notas  = TextAreaField('Notas internas', validators=[Optional()])
    submit = SubmitField('Guardar')
