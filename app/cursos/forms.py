from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, SelectMultipleField,
                     DecimalField, TextAreaField, TimeField,
                     BooleanField, DateField, FloatField, SubmitField)
from wtforms.validators import DataRequired, Optional, NumberRange
from wtforms.widgets import CheckboxInput, ListWidget

DIAS_SEMANA = [
    ('lunes',     'Lunes'),
    ('martes',    'Martes'),
    ('miercoles', 'Miércoles'),
    ('jueves',    'Jueves'),
    ('viernes',   'Viernes'),
    ('sabado',    'Sábado'),
    ('domingo',   'Domingo'),
]

MODALIDADES = [
    ('grupal',     'Grupal'),
    ('individual', 'Individual'),
]

SALAS = [
    ('',       '— Sin asignar —'),
    ('sala_1', 'Sala 1'),
    ('sala_2', 'Sala 2'),
    ('sala_3', 'Sala 3'),
]

class HorarioForm(FlaskForm):
    """Subform para un horario — se usa embebido, no como form independiente."""
    class Meta:
        csrf = False

    dia_semana  = SelectField('Día', choices=DIAS_SEMANA)
    hora_inicio = StringField('Desde', validators=[DataRequired()])
    hora_fin    = StringField('Hasta', validators=[DataRequired()])


class CursoForm(FlaskForm):
    nombre       = StringField('Nombre del curso',
                       validators=[DataRequired()])
    profesor_id  = SelectField('Profesor a cargo',
                       coerce=int,
                       validators=[DataRequired(message='Seleccioná un profesor')])
    modalidad    = SelectField('Modalidad', choices=MODALIDADES,
                       validators=[DataRequired()])
    arancel_base = DecimalField('Arancel base ($)',
                        places=2,
                        validators=[DataRequired(),
                                    NumberRange(min=0, message='Debe ser mayor a 0')])
    sala         = SelectField('Sala', choices=SALAS, validators=[Optional()])
    descripcion  = TextAreaField('Descripción', validators=[Optional()])
    submit       = SubmitField('Guardar')

class InscripcionForm(FlaskForm):
    alumno_id       = SelectField('Alumno', coerce=int,
                          validators=[DataRequired(message='Seleccioná un alumno')])
    arancel_acordado = DecimalField('Arancel acordado ($)',
                           places=2,
                           validators=[DataRequired(),
                                       NumberRange(min=0)])
    descuento_pct   = FloatField('Descuento (%)',
                         validators=[Optional(),
                                     NumberRange(min=0, max=100)],
                         default=0)
    submit = SubmitField('Inscribir')


class ReprogramacionForm(FlaskForm):
    fecha_original = DateField('Fecha original de la clase',
                        validators=[DataRequired()])
    fecha_nueva    = DateField('Nueva fecha',
                        validators=[DataRequired()])
    motivo         = TextAreaField('Motivo', validators=[Optional()])
    cobro_extra    = BooleanField('Aplicar cobro extra')
    monto_extra    = DecimalField('Monto extra ($)',
                         places=2,
                         validators=[Optional(),
                                     NumberRange(min=0)],
                         default=0)
    submit = SubmitField('Guardar reprogramación')
