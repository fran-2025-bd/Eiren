from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps

from app.extensions import db
from app.models import Usuario, ROL_ADMIN, ROL_PROFESOR, ROL_ALUMNO
from app.auth.forms import LoginForm
from . import auth_bp


def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.rol not in roles:
                flash('No tenés permiso para acceder a esa sección.', 'danger')
                return redirect(url_for('auth.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(
            username=form.username.data.strip().lower()
        ).first()

        if usuario and usuario.activo and usuario.check_password(form.password.data):
            login_user(usuario, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('auth.dashboard'))

        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.es_admin():
        return redirect(url_for('auth.dashboard_admin'))
    if current_user.es_profesor():
        return redirect(url_for('auth.dashboard_profesor'))
    return redirect(url_for('auth.dashboard_alumno'))


@auth_bp.route('/dashboard/admin')
@login_required
@rol_requerido(ROL_ADMIN)
def dashboard_admin():
    import json
    from app.models import Clase, Asistencia, CONF_SI

    # Cargar clases de los próximos 3 meses para el calendario
    from datetime import date
    from dateutil.relativedelta import relativedelta

    hoy    = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    fin    = inicio + relativedelta(months=3)

    clases = (Clase.query
              .filter(Clase.fecha >= inicio)
              .filter(Clase.fecha <= fin)
              .order_by(Clase.fecha, Clase.hora_inicio)
              .all())

    clases_json = []
    for c in clases:
        total_alumnos = len(c.asistencias)
        confirmados   = sum(1 for a in c.asistencias if a.confirmacion == CONF_SI)
        clases_json.append({
            'fecha':         c.fecha.isoformat(),
            'curso_id':      c.curso_id,
            'curso_nombre':  c.curso.nombre,
            'hora_inicio':   c.hora_inicio or '',
            'hora_fin':      c.hora_fin or '',
            'estado':        c.estado,
            'profesor':      c.curso.profesor.usuario.nombre,
            'total_alumnos': total_alumnos,
            'confirmados':   confirmados,
            'sala':          c.curso.sala_label() if c.curso.sala else '—',
        })

    return render_template('auth/dashboard_admin.html',
                           clases_json=json.dumps(clases_json))



@auth_bp.route('/dashboard/profesor')
@login_required
@rol_requerido(ROL_PROFESOR)
def dashboard_profesor():
    import json
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from app.models import Clase, CONF_SI

    profesor = current_user.profesor
    if not profesor:
        flash('No se encontró el perfil de profesor.', 'danger')
        return redirect(url_for('auth.logout'))

    hoy    = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    fin    = inicio + relativedelta(months=3)

    # Solo clases de sus cursos
    curso_ids = [c.id for c in profesor.cursos if c.activo]

    clases = []
    if curso_ids:
        clases = (Clase.query
                  .filter(Clase.curso_id.in_(curso_ids))
                  .filter(Clase.fecha >= inicio)
                  .filter(Clase.fecha <= fin)
                  .order_by(Clase.fecha, Clase.hora_inicio)
                  .all())

    clases_json = []
    for c in clases:
        total_alumnos = len(c.asistencias)
        confirmados   = sum(1 for a in c.asistencias if a.confirmacion == CONF_SI)
        clases_json.append({
            'fecha':         c.fecha.isoformat(),
            'curso_id':      c.curso_id,
            'curso_nombre':  c.curso.nombre,
            'hora_inicio':   c.hora_inicio or '',
            'hora_fin':      c.hora_fin or '',
            'estado':        c.estado,
            'profesor':      c.curso.profesor.usuario.nombre,
            'total_alumnos': total_alumnos,
            'confirmados':   confirmados,
            'sala':          c.curso.sala_label() if c.curso.sala else '—',
        })

    return render_template('auth/dashboard_profesor.html',
                           profesor=profesor,
                           clases_json=json.dumps(clases_json))


@auth_bp.route('/dashboard/alumno')
@login_required
@rol_requerido(ROL_ALUMNO)
def dashboard_alumno():
    import json
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from app.models import Clase, CONF_SI, PagoAlumno

    alumno = current_user.alumno
    if not alumno:
        flash('No se encontró el perfil de alumno.', 'danger')
        return redirect(url_for('auth.logout'))

    hoy    = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    fin    = inicio + relativedelta(months=3)

    # Solo clases de sus inscripciones activas
    curso_ids = [i.curso_id for i in alumno.inscripciones if i.activo]

    clases = []
    if curso_ids:
        clases = (Clase.query
                  .filter(Clase.curso_id.in_(curso_ids))
                  .filter(Clase.fecha >= inicio)
                  .filter(Clase.fecha <= fin)
                  .order_by(Clase.fecha, Clase.hora_inicio)
                  .all())

    clases_json = []
    for c in clases:
        # Buscar la asistencia específica de este alumno
        asist = next((a for a in c.asistencias
                      if a.inscripcion.alumno_id == alumno.id), None)
        clases_json.append({
            'fecha':        c.fecha.isoformat(),
            'curso_id':     c.curso_id,
            'curso_nombre': c.curso.nombre,
            'hora_inicio':  c.hora_inicio or '',
            'hora_fin':     c.hora_fin or '',
            'estado':       c.estado,
            'profesor':     c.curso.profesor.usuario.nombre,
            'confirmacion': asist.confirmacion if asist else 'pendiente',
            'asistencia':   asist.asistencia  if asist else 'pendiente',
            'sala':         c.curso.sala_label() if c.curso.sala else '—',
        })

    # Últimos pagos
    todos_pagos = []
    for i in alumno.inscripciones:
        todos_pagos.extend(i.pagos)
    ultimos_pagos = sorted(todos_pagos,
                           key=lambda p: p.fecha_pago,
                           reverse=True)[:5]

    return render_template('auth/dashboard_alumno.html',
                           alumno=alumno,
                           clases_json=json.dumps(clases_json),
                           ultimos_pagos=ultimos_pagos)
