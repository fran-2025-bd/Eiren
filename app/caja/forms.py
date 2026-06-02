from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DecimalField,
                     DateField, TextAreaField, SubmitField, IntegerField)
from wtforms.validators import DataRequired, Optional, NumberRange

TIPOS_PAGO = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
    ('otro',          'Otro'),
]

CATEGORIAS_EGRESO = [
    ('liquidacion_profesor', 'Liquidación profesor'),
    ('gasto_otro',           'Gasto otro'),
]

CATEGORIAS_INGRESO = [
    ('cuota_alumno',               'Cuota alumno'),
    ('cobro_extra_reprogramacion', 'Cobro extra reprogramación'),
    ('ingreso_extraordinario',     'Ingreso extraordinario'),
]


class PagoAlumnoForm(FlaskForm):
    inscripcion_id  = SelectField('Alumno / Curso', coerce=int,
                          validators=[DataRequired()])
    periodo_mes     = SelectField('Mes', coerce=int,
                          choices=[(i, n) for i, n in enumerate(
                              ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
                              0) if i > 0],
                          validators=[DataRequired()])
    periodo_anio    = IntegerField('Año',
                          validators=[DataRequired(),
                                      NumberRange(min=2024, max=2035)])
    monto           = DecimalField('Monto ($)', places=2,
                          validators=[DataRequired(), NumberRange(min=0)])
    tipo_pago       = SelectField('Tipo de pago', choices=TIPOS_PAGO,
                          validators=[DataRequired()])
    fecha_pago      = DateField('Fecha de pago', validators=[DataRequired()])
    comprobante_nro = StringField('N° Comprobante', validators=[Optional()])
    submit          = SubmitField('Registrar pago')


class MovimientoExtraForm(FlaskForm):
    tipo        = SelectField('Tipo', choices=[('ingreso','Ingreso'),('egreso','Egreso')],
                     validators=[DataRequired()])
    categoria   = SelectField('Categoría', choices=[], validators=[DataRequired()])
    descripcion = StringField('Descripción',
                     validators=[DataRequired()])
    monto       = DecimalField('Monto ($)', places=2,
                     validators=[DataRequired(), NumberRange(min=0)])
    cuenta      = SelectField('Cuenta', choices=TIPOS_PAGO,
                     validators=[DataRequired()])
    fecha       = DateField('Fecha', validators=[DataRequired()])
    submit      = SubmitField('Registrar movimiento')


class AjusteCajaForm(FlaskForm):
    cuenta_id   = SelectField('Cuenta', coerce=int, validators=[DataRequired()])
    monto_nuevo = DecimalField('Nuevo saldo ($)', places=2,
                      validators=[DataRequired(), NumberRange(min=0)])
    motivo      = StringField('Motivo del ajuste',
                      validators=[DataRequired()])
    fecha       = DateField('Fecha', validators=[DataRequired()])
    submit      = SubmitField('Aplicar ajuste')


class LiquidacionForm(FlaskForm):
    profesor_id  = SelectField('Profesor', coerce=int, validators=[DataRequired()])
    periodo_mes  = SelectField('Mes', coerce=int,
                      choices=[(i, n) for i, n in enumerate(
                          ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                           'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
                          0) if i > 0],
                      validators=[DataRequired()])
    periodo_anio = IntegerField('Año',
                      validators=[DataRequired(),
                                  NumberRange(min=2024, max=2035)])
    submit       = SubmitField('Calcular liquidación')


class PagarLiquidacionForm(FlaskForm):
    tipo_pago = SelectField('Tipo de pago', choices=TIPOS_PAGO,
                    validators=[DataRequired()])
    fecha     = DateField('Fecha de pago', validators=[DataRequired()])
    submit    = SubmitField('Confirmar pago')
