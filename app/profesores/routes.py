from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Usuario, Profesor, ROL_PROFESOR
from app.profesores.forms import ProfesorForm
from app.auth.routes import rol_requerido
from . import profesores_bp
from app.models import DisponibilidadProfesor, Profesor as ProfesorModel, Usuario

# ------------------------------------------------------------------
# Listado
# ------------------------------------------------------------------
@profesores_bp.route('/')
@login_required
@rol_requerido('admin')
def listado():
    busqueda = request.args.get('q', '').strip()
    query = Profesor.query.join(Usuario)

    if busqueda:
        query = query.filter(
            Usuario.nombre.ilike(f'%{busqueda}%') |
            Profesor.dni.ilike(f'%{busqueda}%')
        )

    profesores = query.order_by(Usuario.nombre).all()
    return render_template('profesores/listado.html',
                           profesores=profesores, busqueda=busqueda)


# ------------------------------------------------------------------
# Alta
# ------------------------------------------------------------------
@profesores_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def nuevo():
    form = ProfesorForm()

    if form.validate_on_submit():
        if Usuario.query.filter_by(
                username=form.username.data.strip().lower()).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('profesores/form.html',
                                   form=form, titulo='Nuevo profesor')

        if not form.password.data:
            flash('La contraseña es obligatoria para un profesor nuevo.', 'danger')
            return render_template('profesores/form.html',
                                   form=form, titulo='Nuevo profesor')

        u = Usuario(
            username = form.username.data.strip().lower(),
            nombre   = form.nombre.data.strip(),
            rol      = ROL_PROFESOR,
            activo   = True,
        )
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.flush()

        p = Profesor(
            usuario_id     = u.id,
            dni            = form.dni.data or None,
            telefono       = form.telefono.data or None,
            email_contacto = form.email_contacto.data or None,
            direccion      = form.direccion.data or None,
            condicion_pago = form.condicion_pago.data or None,
            fecha_nacimiento = form.fecha_nacimiento.data or None,
            notas          = form.notas.data or None,
        )
        db.session.add(p)
        db.session.commit()

        flash(f'Profesor {u.nombre} creado correctamente.', 'success')
        return redirect(url_for('profesores.ficha', profesor_id=p.id))

    return render_template('profesores/form.html', form=form, titulo='Nuevo profesor')


# ------------------------------------------------------------------
# Ficha (ver)
# ------------------------------------------------------------------
@profesores_bp.route('/<int:profesor_id>')
@login_required
@rol_requerido('admin')
def ficha(profesor_id):
    profesor = Profesor.query.get_or_404(profesor_id)
    return render_template('profesores/ficha.html', profesor=profesor)


# ------------------------------------------------------------------
# Editar
# ------------------------------------------------------------------
@profesores_bp.route('/<int:profesor_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def editar(profesor_id):
    profesor = Profesor.query.get_or_404(profesor_id)
    u = profesor.usuario
    form = ProfesorForm(obj=profesor)

    if request.method == 'GET':
        form.username.data      = u.username
        form.nombre.data        = u.nombre
        form.condicion_pago.data = profesor.condicion_pago or ''

    if form.validate_on_submit():
        nuevo_username = form.username.data.strip().lower()

        existe = Usuario.query.filter(
            Usuario.username == nuevo_username,
            Usuario.id != u.id
        ).first()
        if existe:
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('profesores/form.html',
                                   form=form, titulo='Editar profesor',
                                   profesor=profesor)

        u.username = nuevo_username
        u.nombre   = form.nombre.data.strip()
        if form.password.data:
            u.set_password(form.password.data)

        profesor.dni            = form.dni.data or None
        profesor.telefono       = form.telefono.data or None
        profesor.email_contacto = form.email_contacto.data or None
        profesor.direccion      = form.direccion.data or None
        profesor.condicion_pago = form.condicion_pago.data or None
        profesor.notas          = form.notas.data or None
        profesor.fecha_nacimiento = form.fecha_nacimiento.data or None

        db.session.commit()
        flash('Datos actualizados correctamente.', 'success')
        return redirect(url_for('profesores.ficha', profesor_id=profesor.id))

    return render_template('profesores/form.html', form=form,
                           titulo='Editar profesor', profesor=profesor)


# ------------------------------------------------------------------
# Activar / Desactivar
# ------------------------------------------------------------------
@profesores_bp.route('/<int:profesor_id>/toggle', methods=['POST'])
@login_required
@rol_requerido('admin')
def toggle_activo(profesor_id):
    profesor = Profesor.query.get_or_404(profesor_id)
    profesor.usuario.activo = not profesor.usuario.activo
    db.session.commit()
    estado = 'activado' if profesor.usuario.activo else 'desactivado'
    flash(f'Profesor {profesor.usuario.nombre} {estado}.', 'info')
    return redirect(url_for('profesores.listado'))

# ---------------------------------------------------------------
# AListado de alumnos 
# ---------------------------------------------------------------

@profesores_bp.route('/mis-alumnos')
@login_required
@rol_requerido('profesor')
def mis_alumnos():
    profesor = current_user.profesor
    if not profesor:
        flash('No se encontró tu perfil de profesor.', 'danger')
        return redirect(url_for('auth.dashboard'))

    # Recopilar alumnos de todos sus cursos activos sin repetir
    alumnos_vistos = set()
    alumnos = []

    for curso in profesor.cursos:
        if not curso.activo:
            continue
        for inscripcion in curso.alumnos_activos():
            alumno = inscripcion.alumno
            if alumno.id not in alumnos_vistos:
                alumnos_vistos.add(alumno.id)
                alumnos.append({
                    'alumno':  alumno,
                    'cursos':  [i.curso.nombre for i in alumno.inscripciones
                                if i.activo and i.curso.profesor_id == profesor.id],
                })

    alumnos.sort(key=lambda x: x['alumno'].usuario.nombre)

    return render_template('profesores/mis_alumnos.html',
                           alumnos=alumnos, profesor=profesor)

@profesores_bp.route('/<int:profesor_id>/disponibilidad', methods=['POST'])
@login_required
@rol_requerido('admin')
def guardar_disponibilidad(profesor_id):
    profesor = Profesor.query.get_or_404(profesor_id)

    # Eliminar disponibilidades anteriores
    DisponibilidadProfesor.query.filter_by(profesor_id=profesor_id).delete()

    dias    = request.form.getlist('disp_dia')
    inicios = request.form.getlist('disp_inicio')
    fines   = request.form.getlist('disp_fin')

    for dia, inicio, fin in zip(dias, inicios, fines):
        if dia and inicio and fin:
            db.session.add(DisponibilidadProfesor(
                profesor_id = profesor_id,
                dia_semana  = dia,
                hora_inicio = inicio,
                hora_fin    = fin,
            ))

    db.session.commit()
    flash('Disponibilidad actualizada correctamente.', 'success')
    return redirect(url_for('profesores.ficha', profesor_id=profesor_id))
