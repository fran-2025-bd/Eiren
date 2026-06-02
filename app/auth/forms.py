from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Usuario',
                  validators=[DataRequired(message='Requerido'),
                               Length(min=3, max=80, message='Entre 3 y 80 caracteres')])
    password = PasswordField('Contraseña',
                  validators=[DataRequired(message='Requerido'),
                               Length(min=4, message='Mínimo 4 caracteres')])
    remember = BooleanField('Recordarme')
    submit   = SubmitField('Ingresar')
