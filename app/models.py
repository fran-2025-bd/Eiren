from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


ROL_ADMIN    = 'admin'
ROL_PROFESOR = 'profesor'
ROL_ALUMNO   = 'alumno'

# Categorías de caja
CAT_CUOTA          = 'cuota_alumno'
CAT_COBRO_EXTRA    = 'cobro_extra_reprogramacion'
CAT_ING_EXTRA      = 'ingreso_extraordinario'
CAT_LIQ_PROFESOR   = 'liquidacion_profesor'
CAT_GASTO_OTRO     = 'gasto_otro'

CATEGORIAS_INGRESO = [CAT_CUOTA, CAT_COBRO_EXTRA, CAT_ING_EXTRA]
CATEGORIAS_EGRESO  = [CAT_LIQ_PROFESOR, CAT_GASTO_OTRO]

CATEGORIA_LABELS = {
    CAT_CUOTA:        'Cuota alumno',
    CAT_COBRO_EXTRA:  'Cobro extra reprogramación',
    CAT_ING_EXTRA:    'Ingreso extraordinario',
    CAT_LIQ_PROFESOR: 'Liquidación profesor',
    CAT_GASTO_OTRO:   'Gasto otro',
}

CUENTA_EFECTIVO      = 'efectivo'
CUENTA_TRANSFERENCIA = 'transferencia'
CUENTA_OTRO          = 'otro'

# Estados de clase
CLASE_PROGRAMADA = 'programada'
CLASE_REALIZADA  = 'realizada'
CLASE_CANCELADA  = 'cancelada'

# Estados de confirmación
CONF_PENDIENTE = 'pendiente'
CONF_SI        = 'si'
CONF_NO        = 'no'

# Estados de asistencia
ASIST_PENDIENTE     = 'pendiente'
ASIST_PRESENTE      = 'presente'
ASIST_AUSENTE       = 'ausente'
ASIST_AUSENTE_DEUDA = 'ausente_deuda'
ASIST_JUSTIFICADO   = 'justificado'


# ------------------------------------------------------------
# Usuario
# ------------------------------------------------------------
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id        = db.Column(db.Integer, primary_key=True)
    username  = db.Column(db.String(80), unique=True, nullable=False)
    nombre    = db.Column(db.String(120), nullable=False)
    hash_pass = db.Column(db.String(256), nullable=False)
    rol       = db.Column(db.String(20), nullable=False, default=ROL_ALUMNO)
    activo    = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    alumno   = db.relationship('Alumno',   back_populates='usuario', uselist=False)
    profesor = db.relationship('Profesor', back_populates='usuario', uselist=False)

    def set_password(self, password):
        self.hash_pass = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hash_pass, password)

    def es_admin(self):    return self.rol == ROL_ADMIN
    def es_profesor(self): return self.rol == ROL_PROFESOR
    def es_alumno(self):   return self.rol == ROL_ALUMNO

    def __repr__(self):
        return f'<Usuario {self.username} [{self.rol}]>'


# ------------------------------------------------------------
# Alumno
# ------------------------------------------------------------
class Alumno(db.Model):
    __tablename__ = 'alumnos'

    id                  = db.Column(db.Integer, primary_key=True)
    usuario_id          = db.Column(db.Integer, db.ForeignKey('usuarios.id'), unique=True, nullable=False)
    dni                 = db.Column(db.String(20))
    telefono            = db.Column(db.String(30))
    fecha_nacimiento    = db.Column(db.Date)
    direccion           = db.Column(db.String(200))
    email_contacto      = db.Column(db.String(150))
    emergencia_nombre   = db.Column(db.String(120))
    emergencia_telefono = db.Column(db.String(30))
    fecha_alta          = db.Column(db.Date, default=datetime.utcnow)
    notas               = db.Column(db.Text)

    usuario = db.relationship('Usuario', back_populates='alumno')

    def __repr__(self):
        return f'<Alumno {self.usuario.nombre if self.usuario else self.id}>'


# ------------------------------------------------------------
# Profesor
# ------------------------------------------------------------
class Profesor(db.Model):
    __tablename__ = 'profesores'

    id               = db.Column(db.Integer, primary_key=True)
    usuario_id       = db.Column(db.Integer, db.ForeignKey('usuarios.id'), unique=True, nullable=False)
    dni              = db.Column(db.String(20))
    telefono         = db.Column(db.String(30))
    email_contacto   = db.Column(db.String(150))
    direccion        = db.Column(db.String(200))
    condicion_pago   = db.Column(db.String(50))
    fecha_nacimiento = db.Column(db.Date)
    notas            = db.Column(db.Text)

    usuario = db.relationship('Usuario', back_populates='profesor')

    def condicion_pago_label(self):
        labels = {
            'por_cuota': 'Por cuota cobrada',
            'mensual':   'Mensual fijo',
            'por_clase': 'Por clase dictada',
        }
        return labels.get(self.condicion_pago, '—')

    def __repr__(self):
        return f'<Profesor {self.usuario.nombre if self.usuario else self.id}>'


# ------------------------------------------------------------
# Curso
# ------------------------------------------------------------
class Curso(db.Model):
    __tablename__ = 'cursos'

    SALAS = {
        'sala_1': 'Sala 1',
        'sala_2': 'Sala 2',
        'sala_3': 'Sala 3',
    }

    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(120), nullable=False)
    profesor_id  = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=False)
    modalidad    = db.Column(db.String(20), nullable=False, default='grupal')
    arancel_base = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    sala         = db.Column(db.String(20))
    descripcion  = db.Column(db.Text)
    activo       = db.Column(db.Boolean, default=True)
    creado_en    = db.Column(db.DateTime, default=datetime.utcnow)

    profesor      = db.relationship('Profesor', backref='cursos')
    horarios      = db.relationship('HorarioCurso', back_populates='curso',
                                    cascade='all, delete-orphan')
    inscripciones = db.relationship('Inscripcion', back_populates='curso',
                                    cascade='all, delete-orphan')

    def modalidad_label(self):
        return 'Individual' if self.modalidad == 'individual' else 'Grupal'

    def sala_label(self):
        return self.SALAS.get(self.sala, '—')

    def horarios_str(self):
        dias = {'lunes':'Lun','martes':'Mar','miercoles':'Mié',
                'jueves':'Jue','viernes':'Vie','sabado':'Sáb','domingo':'Dom'}
        return ' / '.join(
            f"{dias.get(h.dia_semana, h.dia_semana)} {h.hora_inicio}-{h.hora_fin}"
            for h in self.horarios
        )

    def alumnos_activos(self):
        return [i for i in self.inscripciones if i.activo]

    def __repr__(self):
        return f'<Curso {self.nombre}>'


# ------------------------------------------------------------
# HorarioCurso
# ------------------------------------------------------------
class HorarioCurso(db.Model):
    __tablename__ = 'horarios_curso'

    id          = db.Column(db.Integer, primary_key=True)
    curso_id    = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    dia_semana  = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.String(5), nullable=False)
    hora_fin    = db.Column(db.String(5), nullable=False)

    curso = db.relationship('Curso', back_populates='horarios')

    def __repr__(self):
        return f'<Horario {self.dia_semana} {self.hora_inicio}-{self.hora_fin}>'


# ------------------------------------------------------------
# Inscripcion
# ------------------------------------------------------------
class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'

    id                = db.Column(db.Integer, primary_key=True)
    alumno_id         = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    curso_id          = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    fecha_inscripcion = db.Column(db.Date, default=datetime.utcnow)
    arancel_acordado  = db.Column(db.Numeric(10, 2), nullable=False)
    descuento_pct     = db.Column(db.Float, default=0)
    activo            = db.Column(db.Boolean, default=True)

    alumno           = db.relationship('Alumno', backref='inscripciones')
    curso            = db.relationship('Curso', back_populates='inscripciones')
    reprogramaciones = db.relationship('ClaseReprogramada',
                                       back_populates='inscripcion',
                                       cascade='all, delete-orphan')

    @property
    def arancel_final(self):
        if self.descuento_pct:
            return float(self.arancel_acordado) * (1 - self.descuento_pct / 100)
        return float(self.arancel_acordado)

    def __repr__(self):
        return f'<Inscripcion alumno={self.alumno_id} curso={self.curso_id}>'


# ------------------------------------------------------------
# ClaseReprogramada
# ------------------------------------------------------------
class ClaseReprogramada(db.Model):
    __tablename__ = 'clases_reprogramadas'

    id                    = db.Column(db.Integer, primary_key=True)
    inscripcion_id        = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    fecha_original        = db.Column(db.Date, nullable=False)
    fecha_nueva           = db.Column(db.Date, nullable=False)
    motivo                = db.Column(db.Text)
    numero_reprogramacion = db.Column(db.Integer, default=1)
    cobro_extra           = db.Column(db.Boolean, default=False)
    monto_extra           = db.Column(db.Numeric(10, 2), default=0)
    pagado                = db.Column(db.Boolean, default=False)
    creado_en             = db.Column(db.DateTime, default=datetime.utcnow)

    inscripcion = db.relationship('Inscripcion', back_populates='reprogramaciones')

    def __repr__(self):
        return f'<Reprogramacion {self.fecha_original} → {self.fecha_nueva}>'


# ------------------------------------------------------------
# Clase
# ------------------------------------------------------------
class Clase(db.Model):
    __tablename__ = 'clases'

    id             = db.Column(db.Integer, primary_key=True)
    curso_id       = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    fecha          = db.Column(db.Date, nullable=False)
    fecha_original = db.Column(db.Date)
    hora_inicio    = db.Column(db.String(5))
    hora_fin       = db.Column(db.String(5))
    estado         = db.Column(db.String(20), default=CLASE_PROGRAMADA)
    reprogramada   = db.Column(db.Boolean, default=False)
    motivo_reprog  = db.Column(db.String(200))
    creado_en      = db.Column(db.DateTime, default=datetime.utcnow)

    curso       = db.relationship('Curso', backref='clases')
    asistencias = db.relationship('Asistencia', back_populates='clase',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Clase {self.curso.nombre} {self.fecha}>'


# ------------------------------------------------------------
# Asistencia
# ------------------------------------------------------------
class Asistencia(db.Model):
    __tablename__ = 'asistencias'

    id             = db.Column(db.Integer, primary_key=True)
    clase_id       = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    confirmacion   = db.Column(db.String(20), default=CONF_PENDIENTE)
    asistencia     = db.Column(db.String(20), default=ASIST_PENDIENTE)
    deuda_generada = db.Column(db.Boolean, default=False)
    notificado     = db.Column(db.Boolean, default=False)
    creado_en      = db.Column(db.DateTime, default=datetime.utcnow)

    clase       = db.relationship('Clase', back_populates='asistencias')
    inscripcion = db.relationship('Inscripcion', backref='asistencias')

    def __repr__(self):
        return f'<Asistencia clase={self.clase_id} insc={self.inscripcion_id}>'


# ------------------------------------------------------------
# DeudaAsistencia
# ------------------------------------------------------------
class DeudaAsistencia(db.Model):
    __tablename__ = 'deudas_asistencia'

    id             = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    clase_id       = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    monto          = db.Column(db.Numeric(10, 2), default=0)
    pagado         = db.Column(db.Boolean, default=False)
    creado_en      = db.Column(db.DateTime, default=datetime.utcnow)

    inscripcion = db.relationship('Inscripcion', backref='deudas_asistencia')
    clase       = db.relationship('Clase')

    def __repr__(self):
        return f'<DeudaAsistencia insc={self.inscripcion_id} pagado={self.pagado}>'


# ------------------------------------------------------------
# CuentaCaja
# ------------------------------------------------------------
class CuentaCaja(db.Model):
    __tablename__ = 'cuentas_caja'

    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(50), unique=True, nullable=False)
    saldo_inicial = db.Column(db.Numeric(12, 2), default=0)
    activo        = db.Column(db.Boolean, default=True)

    movimientos = db.relationship('MovimientoCaja', back_populates='cuenta')
    ajustes     = db.relationship('AjusteCaja', back_populates='cuenta')

    @property
    def saldo_actual(self):
        ingresos = sum(float(m.monto) for m in self.movimientos if m.tipo == 'ingreso')
        egresos  = sum(float(m.monto) for m in self.movimientos if m.tipo == 'egreso')
        return float(self.saldo_inicial) + ingresos - egresos

    def __repr__(self):
        return f'<CuentaCaja {self.nombre}>'


# ------------------------------------------------------------
# MovimientoCaja
# ------------------------------------------------------------
class MovimientoCaja(db.Model):
    __tablename__ = 'movimientos_caja'

    id              = db.Column(db.Integer, primary_key=True)
    cuenta_id       = db.Column(db.Integer, db.ForeignKey('cuentas_caja.id'), nullable=False)
    tipo            = db.Column(db.String(10), nullable=False)
    categoria       = db.Column(db.String(50), nullable=False)
    descripcion     = db.Column(db.String(300))
    monto           = db.Column(db.Numeric(12, 2), nullable=False)
    fecha           = db.Column(db.Date, nullable=False)
    referencia_id   = db.Column(db.Integer)
    referencia_tipo = db.Column(db.String(50))
    creado_por_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    creado_en       = db.Column(db.DateTime, default=datetime.utcnow)

    cuenta     = db.relationship('CuentaCaja', back_populates='movimientos')
    creado_por = db.relationship('Usuario')

    @property
    def categoria_label(self):
        return CATEGORIA_LABELS.get(self.categoria, self.categoria)

    def __repr__(self):
        return f'<Movimiento {self.tipo} ${self.monto} {self.fecha}>'


# ------------------------------------------------------------
# PagoAlumno
# ------------------------------------------------------------
class PagoAlumno(db.Model):
    __tablename__ = 'pagos_alumnos'

    id              = db.Column(db.Integer, primary_key=True)
    inscripcion_id  = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    periodo_mes     = db.Column(db.Integer, nullable=False)
    periodo_anio    = db.Column(db.Integer, nullable=False)
    monto           = db.Column(db.Numeric(12, 2), nullable=False)
    tipo_pago       = db.Column(db.String(20), nullable=False)
    fecha_pago      = db.Column(db.Date, nullable=False)
    comprobante_nro = db.Column(db.String(50))
    movimiento_id   = db.Column(db.Integer, db.ForeignKey('movimientos_caja.id'))
    creado_en       = db.Column(db.DateTime, default=datetime.utcnow)

    inscripcion = db.relationship('Inscripcion', backref='pagos')
    movimiento  = db.relationship('MovimientoCaja')

    @property
    def periodo_str(self):
        meses = ['','Ene','Feb','Mar','Abr','May','Jun',
                 'Jul','Ago','Sep','Oct','Nov','Dic']
        return f"{meses[self.periodo_mes]} {self.periodo_anio}"

    def __repr__(self):
        return f'<PagoAlumno insc={self.inscripcion_id} {self.periodo_str}>'


# ------------------------------------------------------------
# LiquidacionProfesor
# ------------------------------------------------------------
class LiquidacionProfesor(db.Model):
    __tablename__ = 'liquidaciones_profesor'

    id               = db.Column(db.Integer, primary_key=True)
    profesor_id      = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=False)
    periodo_mes      = db.Column(db.Integer, nullable=False)
    periodo_anio     = db.Column(db.Integer, nullable=False)
    monto_confirmado = db.Column(db.Numeric(12, 2), default=0)
    monto_pendiente  = db.Column(db.Numeric(12, 2), default=0)
    estado           = db.Column(db.String(20), default='borrador')
    fecha_pago       = db.Column(db.Date)
    tipo_pago        = db.Column(db.String(20))
    movimiento_id    = db.Column(db.Integer, db.ForeignKey('movimientos_caja.id'))
    creado_en        = db.Column(db.DateTime, default=datetime.utcnow)

    profesor   = db.relationship('Profesor', backref='liquidaciones')
    movimiento = db.relationship('MovimientoCaja')
    items      = db.relationship('LiquidacionItem', back_populates='liquidacion',
                                 cascade='all, delete-orphan')

    @property
    def periodo_str(self):
        meses = ['','Ene','Feb','Mar','Abr','May','Jun',
                 'Jul','Ago','Sep','Oct','Nov','Dic']
        return f"{meses[self.periodo_mes]} {self.periodo_anio}"

    @property
    def monto_total(self):
        return float(self.monto_confirmado) + float(self.monto_pendiente)

    def __repr__(self):
        return f'<Liquidacion prof={self.profesor_id} {self.periodo_str}>'


# ------------------------------------------------------------
# LiquidacionItem
# ------------------------------------------------------------
class LiquidacionItem(db.Model):
    __tablename__ = 'liquidacion_items'

    id               = db.Column(db.Integer, primary_key=True)
    liquidacion_id   = db.Column(db.Integer, db.ForeignKey('liquidaciones_profesor.id'), nullable=False)
    inscripcion_id   = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    clases_dadas     = db.Column(db.Integer, default=0)
    clases_asistidas = db.Column(db.Integer, default=0)
    arancel_acordado = db.Column(db.Numeric(12, 2), default=0)
    monto_calculado  = db.Column(db.Numeric(12, 2), default=0)
    pago_alumno_id   = db.Column(db.Integer, db.ForeignKey('pagos_alumnos.id'))

    liquidacion = db.relationship('LiquidacionProfesor', back_populates='items')
    inscripcion = db.relationship('Inscripcion')
    pago_alumno = db.relationship('PagoAlumno')

    @property
    def pendiente(self):
        return self.pago_alumno_id is None

    def __repr__(self):
        return f'<LiquidacionItem liq={self.liquidacion_id} insc={self.inscripcion_id}>'


# ------------------------------------------------------------
# AjusteCaja
# ------------------------------------------------------------
class AjusteCaja(db.Model):
    __tablename__ = 'ajustes_caja'

    id             = db.Column(db.Integer, primary_key=True)
    cuenta_id      = db.Column(db.Integer, db.ForeignKey('cuentas_caja.id'), nullable=False)
    monto_anterior = db.Column(db.Numeric(12, 2), nullable=False)
    monto_nuevo    = db.Column(db.Numeric(12, 2), nullable=False)
    motivo         = db.Column(db.String(300), nullable=False)
    fecha          = db.Column(db.Date, nullable=False)
    creado_por_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    creado_en      = db.Column(db.DateTime, default=datetime.utcnow)

    cuenta     = db.relationship('CuentaCaja', back_populates='ajustes')
    creado_por = db.relationship('Usuario')

    def __repr__(self):
        return f'<AjusteCaja cuenta={self.cuenta_id} {self.fecha}>'


# ------------------------------------------------------------
# Flask-Login loader
# ------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))