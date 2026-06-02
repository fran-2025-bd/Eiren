from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import db
from app.models import Usuario, ROL_ADMIN, ROL_PROFESOR, ROL_ALUMNO
from app.usuarios.forms import CambiarPasswordForm, EditarUsuarioForm
from app.auth.routes import rol_requerido
from . import usuarios_bp


# ------------------------------------------------------------------
# Listado de usuarios
# ------------------------------------------------------------------
@usuarios_bp.route('/')
@login_required
@rol_requerido('admin')
def listado():
    busqueda = request.args.get('q', '').strip()
    rol      = request.args.get('rol', '')

    query = Usuario.query

    if busqueda:
        query = query.filter(
            Usuario.nombre.ilike(f'%{busqueda}%') |
            Usuario.username.ilike(f'%{busqueda}%')
        )
    if rol:
        query = query.filter_by(rol=rol)

    usuarios = query.order_by(Usuario.rol, Usuario.nombre).all()

    return render_template('usuarios/listado.html',
                           usuarios=usuarios,
                           busqueda=busqueda,
                           rol_filtro=rol)


# ------------------------------------------------------------------
# Ver / Editar usuario
# ------------------------------------------------------------------
@usuarios_bp.route('/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def editar(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    form    = EditarUsuarioForm(obj=usuario)

    if request.method == 'GET':
        form.nombre.data   = usuario.nombre
        form.username.data = usuario.username
        form.rol.data      = usuario.rol
        form.activo.data   = usuario.activo

    if form.validate_on_submit():
        nuevo_username = form.username.data.strip().lower()

        # Verificar username único
        existe = Usuario.query.filter(
            Usuario.username == nuevo_username,
            Usuario.id != usuario.id
        ).first()
        if existe:
            flash('El nombre de usuario ya está en uso.', 'danger')
            return render_template('usuarios/editar.html',
                                   form=form, usuario=usuario)

        usuario.nombre   = form.nombre.data.strip()
        usuario.username = nuevo_username
        usuario.rol      = form.rol.data
        usuario.activo   = form.activo.data
        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('usuarios.listado'))

    return render_template('usuarios/editar.html', form=form, usuario=usuario)


# ------------------------------------------------------------------
# Cambiar contraseña
# ------------------------------------------------------------------
@usuarios_bp.route('/<int:usuario_id>/password', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def cambiar_password(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    form    = CambiarPasswordForm()

    if form.validate_on_submit():
        usuario.set_password(form.password_nueva.data)
        db.session.commit()
        flash(f'Contraseña de {usuario.nombre} actualizada correctamente.', 'success')
        return redirect(url_for('usuarios.listado'))

    return render_template('usuarios/cambiar_password.html',
                           form=form, usuario=usuario)


# ------------------------------------------------------------------
# Activar / Desactivar
# ------------------------------------------------------------------
@usuarios_bp.route('/<int:usuario_id>/toggle', methods=['POST'])
@login_required
@rol_requerido('admin')
def toggle_activo(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    # No permitir desactivar al propio admin
    from flask_login import current_user
    if usuario.id == current_user.id:
        flash('No podés desactivar tu propio usuario.', 'danger')
        return redirect(url_for('usuarios.listado'))

    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f'Usuario {usuario.nombre} {estado}.', 'info')
    return redirect(url_for('usuarios.listado'))
