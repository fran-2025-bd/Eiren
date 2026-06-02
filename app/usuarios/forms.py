from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

ROLES = [
    ('admin',    'Administrador'),
    ('profesor', 'Profesor'),
    ('alumno',   'Alumno'),
]

class CambiarPasswordForm(FlaskForm):
    password_nueva    = PasswordField('Nueva contraseña',
                            validators=[DataRequired(),
                                        Length(min=4, message='Mínimo 4 caracteres')])
    password_confirmar = PasswordField('Confirmar contraseña',
                            validators=[DataRequired()])
    submit = SubmitField('Cambiar contraseña')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.password_nueva.data != self.password_confirmar.data:
            self.password_confirmar.errors.append('Las contraseñas no coinciden.')
            return False
        return True


class EditarUsuarioForm(FlaskForm):
    nombre  = StringField('Nombre completo',
                  validators=[DataRequired(), Length(max=120)])
    username = StringField('Usuario',
                  validators=[DataRequired(), Length(min=3, max=80)])
    rol     = SelectField('Rol', choices=ROLES, validators=[DataRequired()])
    activo  = BooleanField('Usuario activo')
    submit  = SubmitField('Guardar')
