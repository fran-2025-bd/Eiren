from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Usuario, Alumno, ROL_ALUMNO
from app.alumnos.forms import AlumnoForm
from app.auth.routes import rol_requerido
from . import alumnos_bp


# ------------------------------------------------------------------
# Listado
# ------------------------------------------------------------------
@alumnos_bp.route('/')
@login_required
@rol_requerido('admin')
def listado():
    busqueda = request.args.get('q', '').strip()
    query = Alumno.query.join(Usuario)

    if busqueda:
        query = query.filter(
            Usuario.nombre.ilike(f'%{busqueda}%') |
            Alumno.dni.ilike(f'%{busqueda}%')
        )

    alumnos = query.order_by(Usuario.nombre).all()
    return render_template('alumnos/listado.html', alumnos=alumnos, busqueda=busqueda)


# ------------------------------------------------------------------
# Alta
# ------------------------------------------------------------------
@alumnos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def nuevo():
    form = AlumnoForm()

    if form.validate_on_submit():
        # Verificar username único
        if Usuario.query.filter_by(username=form.username.data.strip().lower()).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('alumnos/form.html', form=form, titulo='Nuevo alumno')

        if not form.password.data:
            flash('La contraseña es obligatoria para un alumno nuevo.', 'danger')
            return render_template('alumnos/form.html', form=form, titulo='Nuevo alumno')

        # Crear usuario
        u = Usuario(
            username = form.username.data.strip().lower(),
            nombre   = form.nombre.data.strip(),
            rol      = ROL_ALUMNO,
            activo   = True,
        )
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.flush()  # obtener ID antes del commit

        # Crear perfil alumno
        a = Alumno(
            usuario_id          = u.id,
            dni                 = form.dni.data or None,
            telefono            = form.telefono.data or None,
            fecha_nacimiento    = form.fecha_nacimiento.data or None,
            direccion           = form.direccion.data or None,
            email_contacto      = form.email_contacto.data or None,
            emergencia_nombre   = form.emergencia_nombre.data or None,
            emergencia_telefono = form.emergencia_telefono.data or None,
            notas               = form.notas.data or None,
        )
        db.session.add(a)
        db.session.commit()

        flash(f'Alumno {u.nombre} creado correctamente.', 'success')
        return redirect(url_for('alumnos.ficha', alumno_id=a.id))

    return render_template('alumnos/form.html', form=form, titulo='Nuevo alumno')


# ------------------------------------------------------------------
# Ficha (ver)
# ------------------------------------------------------------------
@alumnos_bp.route('/<int:alumno_id>')
@login_required
@rol_requerido('admin', 'profesor')
def ficha(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    return render_template('alumnos/ficha.html', alumno=alumno)


# ------------------------------------------------------------------
# Editar
# ------------------------------------------------------------------
@alumnos_bp.route('/<int:alumno_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def editar(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    u = alumno.usuario
    form = AlumnoForm(obj=alumno)

    if request.method == 'GET':
        # Precargar campos del usuario
        form.username.data = u.username
        form.nombre.data   = u.nombre

    if form.validate_on_submit():
        nuevo_username = form.username.data.strip().lower()

        # Verificar username único (excluir el propio)
        existe = Usuario.query.filter(
            Usuario.username == nuevo_username,
            Usuario.id != u.id
        ).first()
        if existe:
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('alumnos/form.html', form=form,
                                   titulo='Editar alumno', alumno=alumno)

        # Actualizar usuario
        u.username = nuevo_username
        u.nombre   = form.nombre.data.strip()
        if form.password.data:
            u.set_password(form.password.data)

        # Actualizar perfil
        alumno.dni                 = form.dni.data or None
        alumno.telefono            = form.telefono.data or None
        alumno.fecha_nacimiento    = form.fecha_nacimiento.data or None
        alumno.direccion           = form.direccion.data or None
        alumno.email_contacto      = form.email_contacto.data or None
        alumno.emergencia_nombre   = form.emergencia_nombre.data or None
        alumno.emergencia_telefono = form.emergencia_telefono.data or None
        alumno.notas               = form.notas.data or None

        db.session.commit()
        flash('Datos actualizados correctamente.', 'success')
        return redirect(url_for('alumnos.ficha', alumno_id=alumno.id))

    return render_template('alumnos/form.html', form=form,
                           titulo='Editar alumno', alumno=alumno)


# ------------------------------------------------------------------
# Activar / Desactivar
# ------------------------------------------------------------------
@alumnos_bp.route('/<int:alumno_id>/toggle', methods=['POST'])
@login_required
@rol_requerido('admin')
def toggle_activo(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    alumno.usuario.activo = not alumno.usuario.activo
    db.session.commit()
    estado = 'activado' if alumno.usuario.activo else 'desactivado'
    flash(f'Alumno {alumno.usuario.nombre} {estado}.', 'info')
    return redirect(url_for('alumnos.listado'))


# ---------------------------------------------------------------
# Esta ruta permite al alumno editar su propio teléfono y email
# ---------------------------------------------------------------

@alumnos_bp.route('/mi-perfil', methods=['GET', 'POST'])
@login_required
@rol_requerido('alumno')
def editar_perfil():
    from flask_wtf import FlaskForm
    from wtforms import StringField, SubmitField
    from wtforms.validators import Optional, Length

    class PerfilForm(FlaskForm):
        telefono       = StringField('Teléfono',          validators=[Optional(), Length(max=30)])
        email_contacto = StringField('Email de contacto', validators=[Optional(), Length(max=150)])
        submit         = SubmitField('Guardar cambios')

    alumno = current_user.alumno
    if not alumno:
        flash('No se encontró tu perfil.', 'danger')
        return redirect(url_for('auth.dashboard'))

    form = PerfilForm(obj=alumno)

    if form.validate_on_submit():
        alumno.telefono       = form.telefono.data or None
        alumno.email_contacto = form.email_contacto.data or None
        db.session.commit()
        flash('Tu perfil fue actualizado correctamente.', 'success')
        return redirect(url_for('auth.dashboard_alumno'))

    return render_template('alumnos/editar_perfil.html', form=form, alumno=alumno)
