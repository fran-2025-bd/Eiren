from decimal import Decimal
from datetime import date
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (Curso, HorarioCurso, Inscripcion, ClaseReprogramada,
                        Profesor, Alumno, Clase, Asistencia,
                        DisponibilidadProfesor,
                        CLASE_PROGRAMADA, CONF_PENDIENTE, ASIST_PENDIENTE)
from app.cursos.forms import CursoForm, InscripcionForm, ReprogramacionForm
from app.auth.routes import rol_requerido
from . import cursos_bp


def _poblar_profesores(form):
    form.profesor_id.choices = [
        (p.id, p.usuario.nombre)
        for p in Profesor.query.join(Profesor.usuario)
                               .filter_by(activo=True)
                               .order_by('nombre').all()
    ]


def _poblar_alumnos(form, curso_id):
    inscriptos = {i.alumno_id for i in
                  Inscripcion.query.filter_by(curso_id=curso_id, activo=True).all()}
    alumnos = Alumno.query.join(Alumno.usuario).filter_by(activo=True).all()
    form.alumno_id.choices = [
        (a.id, a.usuario.nombre)
        for a in alumnos if a.id not in inscriptos
    ]


def _validar_sala(sala, horarios_nuevos, curso_id=None):
    """
    Verifica que la sala no tenga conflicto de horario con otro curso activo.
    Retorna lista de conflictos o [] si no hay.
    """
    if not sala:
        return []

    conflictos = []
    for h_nuevo in horarios_nuevos:
        query = (HorarioCurso.query
                 .join(Curso)
                 .filter(Curso.sala == sala)
                 .filter(Curso.activo == True)
                 .filter(HorarioCurso.dia_semana == h_nuevo['dia_semana']))

        if curso_id:
            query = query.filter(Curso.id != curso_id)

        for h_exist in query.all():
            if h_nuevo['hora_inicio'] < h_exist.hora_fin and h_nuevo['hora_fin'] > h_exist.hora_inicio:
                conflictos.append(
                    f"{h_exist.curso.nombre} — {h_nuevo['dia_semana'].capitalize()} "
                    f"{h_exist.hora_inicio}–{h_exist.hora_fin}"
                )
    return conflictos


def _validar_disponibilidad_profesor(profesor_id, horarios_nuevos, curso_id=None):
    """
    Verifica que el profesor:
    1. Tenga disponibilidad declarada en ese día y horario
    2. No tenga otro curso en ese mismo horario
    Retorna lista de errores o [] si todo está OK.
    """
    errores = []

    for h in horarios_nuevos:
        dia    = h['dia_semana']
        inicio = h['hora_inicio']
        fin    = h['hora_fin']

        # 1. Verificar disponibilidad declarada
        disponibilidades = DisponibilidadProfesor.query.filter_by(
            profesor_id=profesor_id,
            dia_semana=dia
        ).all()

        tiene_disp = any(
            d.hora_inicio <= inicio and d.hora_fin >= fin
            for d in disponibilidades
        )

        if not tiene_disp:
            prof = Profesor.query.get(profesor_id)
            nombre = prof.usuario.nombre if prof else f'Profesor {profesor_id}'
            errores.append(
                f"{nombre} no tiene disponibilidad declarada el "
                f"{dia.capitalize()} {inicio}–{fin}"
            )
            continue

        # 2. Verificar que no tenga otro curso en ese horario
        query = (HorarioCurso.query
                 .join(Curso)
                 .filter(Curso.profesor_id == profesor_id)
                 .filter(Curso.activo == True)
                 .filter(HorarioCurso.dia_semana == dia))

        if curso_id:
            query = query.filter(Curso.id != curso_id)

        for h_exist in query.all():
            if inicio < h_exist.hora_fin and fin > h_exist.hora_inicio:
                errores.append(
                    f"Profesor ya tiene '{h_exist.curso.nombre}' el "
                    f"{dia.capitalize()} {h_exist.hora_inicio}–{h_exist.hora_fin}"
                )

    return errores


# ------------------------------------------------------------------
# Listado
# ------------------------------------------------------------------
@cursos_bp.route('/')
@login_required
@rol_requerido('admin', 'profesor')
def listado():
    busqueda = request.args.get('q', '').strip()
    query = Curso.query

    if current_user.es_profesor():
        query = query.filter_by(profesor_id=current_user.profesor.id)

    if busqueda:
        query = query.filter(Curso.nombre.ilike(f'%{busqueda}%'))

    cursos = query.order_by(Curso.nombre).all()
    return render_template('cursos/listado.html', cursos=cursos, busqueda=busqueda)


# ------------------------------------------------------------------
# Nuevo curso
# ------------------------------------------------------------------
@cursos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def nuevo():
    form = CursoForm()
    _poblar_profesores(form)

    if form.validate_on_submit():
        dias    = request.form.getlist('dia_semana')
        inicios = request.form.getlist('hora_inicio')
        fines   = request.form.getlist('hora_fin')

        horarios_data = [
            {'dia_semana': dia, 'hora_inicio': inicio, 'hora_fin': fin}
            for dia, inicio, fin in zip(dias, inicios, fines)
            if dia and inicio and fin
        ]

        sala = form.sala.data or None
        if sala:
            conflictos = _validar_sala(sala, horarios_data)
            if conflictos:
                flash(f'Conflicto de sala: {", ".join(conflictos)}', 'danger')
                return render_template('cursos/form.html', form=form,
                                       titulo='Nuevo curso', horarios=[])

        errores_prof = _validar_disponibilidad_profesor(
            form.profesor_id.data, horarios_data)
        if errores_prof:
            flash(f'Conflicto de profesor: {", ".join(errores_prof)}', 'danger')
            return render_template('cursos/form.html', form=form,
                                   titulo='Nuevo curso', horarios=[])

        curso = Curso(
            nombre       = form.nombre.data.strip(),
            profesor_id  = form.profesor_id.data,
            modalidad    = form.modalidad.data,
            arancel_base = form.arancel_base.data,
            sala         = sala,
            descripcion  = form.descripcion.data or None,
            activo       = True,
        )
        db.session.add(curso)
        db.session.flush()

        for h in horarios_data:
            db.session.add(HorarioCurso(
                curso_id    = curso.id,
                dia_semana  = h['dia_semana'],
                hora_inicio = h['hora_inicio'],
                hora_fin    = h['hora_fin'],
            ))

        db.session.commit()
        flash(f'Curso "{curso.nombre}" creado correctamente.', 'success')
        return redirect(url_for('cursos.ficha', curso_id=curso.id))

    return render_template('cursos/form.html', form=form, titulo='Nuevo curso', horarios=[])


# ------------------------------------------------------------------
# Ficha del curso
# ------------------------------------------------------------------
@cursos_bp.route('/<int:curso_id>')
@login_required
@rol_requerido('admin', 'profesor')
def ficha(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    return render_template('cursos/ficha.html', curso=curso)


# ------------------------------------------------------------------
# Editar curso
# ------------------------------------------------------------------
@cursos_bp.route('/<int:curso_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def editar(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    form = CursoForm(obj=curso)
    _poblar_profesores(form)

    if request.method == 'GET':
        form.profesor_id.data  = curso.profesor_id
        form.modalidad.data    = curso.modalidad
        form.arancel_base.data = curso.arancel_base
        form.sala.data         = curso.sala or ''

    if form.validate_on_submit():
        dias    = request.form.getlist('dia_semana')
        inicios = request.form.getlist('hora_inicio')
        fines   = request.form.getlist('hora_fin')

        horarios_data = [
            {'dia_semana': dia, 'hora_inicio': inicio, 'hora_fin': fin}
            for dia, inicio, fin in zip(dias, inicios, fines)
            if dia and inicio and fin
        ]

        sala = form.sala.data or None
        if sala:
            conflictos = _validar_sala(sala, horarios_data, curso_id=curso.id)
            if conflictos:
                flash(f'Conflicto de sala: {", ".join(conflictos)}', 'danger')
                return render_template('cursos/form.html', form=form,
                                       titulo='Editar curso',
                                       horarios=curso.horarios, curso=curso)

        errores_prof = _validar_disponibilidad_profesor(
            form.profesor_id.data, horarios_data, curso_id=curso.id)
        if errores_prof:
            flash(f'Conflicto de profesor: {", ".join(errores_prof)}', 'danger')
            return render_template('cursos/form.html', form=form,
                                   titulo='Editar curso',
                                   horarios=curso.horarios, curso=curso)

        curso.nombre       = form.nombre.data.strip()
        curso.profesor_id  = form.profesor_id.data
        curso.modalidad    = form.modalidad.data
        curso.arancel_base = form.arancel_base.data
        curso.sala         = sala
        curso.descripcion  = form.descripcion.data or None

        for h in curso.horarios:
            db.session.delete(h)
        db.session.flush()

        for h in horarios_data:
            db.session.add(HorarioCurso(
                curso_id    = curso.id,
                dia_semana  = h['dia_semana'],
                hora_inicio = h['hora_inicio'],
                hora_fin    = h['hora_fin'],
            ))

        db.session.commit()
        flash('Curso actualizado correctamente.', 'success')
        return redirect(url_for('cursos.ficha', curso_id=curso.id))

    return render_template('cursos/form.html', form=form,
                           titulo='Editar curso', horarios=curso.horarios, curso=curso)


# ------------------------------------------------------------------
# Activar / Desactivar curso
# ------------------------------------------------------------------
@cursos_bp.route('/<int:curso_id>/toggle', methods=['POST'])
@login_required
@rol_requerido('admin')
def toggle_activo(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    curso.activo = not curso.activo
    db.session.commit()
    estado = 'activado' if curso.activo else 'desactivado'
    flash(f'Curso "{curso.nombre}" {estado}.', 'info')
    return redirect(url_for('cursos.listado'))


# ------------------------------------------------------------------
# Inscribir alumno al curso
# ------------------------------------------------------------------
@cursos_bp.route('/<int:curso_id>/inscribir', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def inscribir(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    form  = InscripcionForm()
    _poblar_alumnos(form, curso_id)

    if request.method == 'GET':
        form.arancel_acordado.data = curso.arancel_base

    if form.validate_on_submit():
        existe = Inscripcion.query.filter_by(
            alumno_id=form.alumno_id.data,
            curso_id=curso_id,
            activo=True
        ).first()
        if existe:
            flash('El alumno ya está inscripto en este curso.', 'warning')
            return render_template('cursos/inscribir.html', form=form, curso=curso)

        inscripcion = Inscripcion(
            alumno_id        = form.alumno_id.data,
            curso_id         = curso_id,
            arancel_acordado = form.arancel_acordado.data,
            descuento_pct    = form.descuento_pct.data or 0,
            activo           = True,
        )
        db.session.add(inscripcion)
        db.session.flush()

        clases_futuras = (Clase.query
                          .filter_by(curso_id=curso_id, estado=CLASE_PROGRAMADA)
                          .filter(Clase.fecha >= date.today())
                          .all())

        for clase in clases_futuras:
            existe_asist = Asistencia.query.filter_by(
                clase_id       = clase.id,
                inscripcion_id = inscripcion.id
            ).first()
            if not existe_asist:
                db.session.add(Asistencia(
                    clase_id       = clase.id,
                    inscripcion_id = inscripcion.id,
                    confirmacion   = CONF_PENDIENTE,
                    asistencia     = ASIST_PENDIENTE,
                ))

        db.session.commit()

        alumno = Alumno.query.get(form.alumno_id.data)
        if clases_futuras:
            flash(f'{alumno.usuario.nombre} inscripto correctamente. '
                  f'Se agregó a {len(clases_futuras)} clase(s) programada(s).', 'success')
        else:
            flash(f'{alumno.usuario.nombre} inscripto correctamente.', 'success')

        return redirect(url_for('cursos.ficha', curso_id=curso_id))

    return render_template('cursos/inscribir.html', form=form, curso=curso)


# ------------------------------------------------------------------
# Dar de baja inscripción
# ------------------------------------------------------------------
@cursos_bp.route('/inscripcion/<int:inscripcion_id>/baja', methods=['POST'])
@login_required
@rol_requerido('admin')
def baja_inscripcion(inscripcion_id):
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    curso_id = inscripcion.curso_id
    inscripcion.activo = False
    db.session.commit()
    flash('Alumno dado de baja del curso.', 'info')
    return redirect(url_for('cursos.ficha', curso_id=curso_id))


# ------------------------------------------------------------------
# Editar inscripción (arancel)
# ------------------------------------------------------------------
@cursos_bp.route('/inscripcion/<int:inscripcion_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def editar_inscripcion(inscripcion_id):
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    form = InscripcionForm(obj=inscripcion)
    form.alumno_id.choices = [(inscripcion.alumno_id, inscripcion.alumno.usuario.nombre)]

    if form.validate_on_submit():
        inscripcion.arancel_acordado = form.arancel_acordado.data
        inscripcion.descuento_pct    = form.descuento_pct.data or 0
        db.session.commit()
        flash('Arancel actualizado correctamente.', 'success')
        return redirect(url_for('cursos.ficha', curso_id=inscripcion.curso_id))

    return render_template('cursos/editar_inscripcion.html',
                           form=form, inscripcion=inscripcion)


# ------------------------------------------------------------------
# Reprogramar clase individual (caso excepcional)
# ------------------------------------------------------------------
@cursos_bp.route('/inscripcion/<int:inscripcion_id>/reprogramar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def reprogramar(inscripcion_id):
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    form = ReprogramacionForm()

    total_prev = ClaseReprogramada.query.filter_by(
        inscripcion_id=inscripcion_id).count()
    numero = total_prev + 1

    if form.validate_on_submit():
        reprog = ClaseReprogramada(
            inscripcion_id        = inscripcion_id,
            fecha_original        = form.fecha_original.data,
            fecha_nueva           = form.fecha_nueva.data,
            motivo                = form.motivo.data or None,
            numero_reprogramacion = numero,
            cobro_extra           = form.cobro_extra.data,
            monto_extra           = form.monto_extra.data if form.cobro_extra.data else 0,
            pagado                = False,
        )
        db.session.add(reprog)
        db.session.commit()

        msg = 'Clase reprogramada correctamente.'
        if form.cobro_extra.data:
            msg += f' Se registró un cobro extra de ${form.monto_extra.data}.'
        flash(msg, 'success')
        return redirect(url_for('cursos.ficha', curso_id=inscripcion.curso_id))

    return render_template('cursos/reprogramar.html',
                           form=form, inscripcion=inscripcion, numero=numero)