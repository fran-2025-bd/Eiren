from datetime import date, datetime, timedelta
from calendar import monthrange
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (Curso, Clase, Asistencia, DeudaAsistencia,
                        Inscripcion, HorarioCurso,
                        CLASE_PROGRAMADA, CLASE_REALIZADA, CLASE_CANCELADA,
                        CONF_PENDIENTE, CONF_SI, CONF_NO,
                        ASIST_PENDIENTE, ASIST_PRESENTE, ASIST_AUSENTE,
                        ASIST_AUSENTE_DEUDA, ASIST_JUSTIFICADO)
from app.auth.routes import rol_requerido
from . import asistencia_bp

DIAS_MAP = {
    'lunes': 0, 'martes': 1, 'miercoles': 2,
    'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6
}


# ------------------------------------------------------------------
# Generar clases del mes para un curso
# ------------------------------------------------------------------
def generar_clases_mes(curso_id, anio, mes):
    """
    Genera las clases del mes según los horarios del curso.
    No duplica si ya existen.
    Retorna la cantidad de clases creadas.
    """
    curso = Curso.query.get(curso_id)
    if not curso or not curso.horarios:
        return 0

    _, dias_en_mes = monthrange(anio, mes)
    creadas = 0

    for horario in curso.horarios:
        dia_semana = DIAS_MAP.get(horario.dia_semana)
        if dia_semana is None:
            continue

        for dia in range(1, dias_en_mes + 1):
            fecha = date(anio, mes, dia)
            if fecha.weekday() != dia_semana:
                continue

            # Verificar si ya existe
            existe = Clase.query.filter_by(
                curso_id=curso_id, fecha=fecha,
                hora_inicio=horario.hora_inicio
            ).first()
            if existe:
                continue

            clase = Clase(
                curso_id    = curso_id,
                fecha       = fecha,
                hora_inicio = horario.hora_inicio,
                hora_fin    = horario.hora_fin,
                estado      = CLASE_PROGRAMADA,
            )
            db.session.add(clase)
            db.session.flush()

            # Crear asistencia para cada alumno inscripto activo
            for inscripcion in curso.inscripciones:
                if not inscripcion.activo:
                    continue
                asist = Asistencia(
                    clase_id       = clase.id,
                    inscripcion_id = inscripcion.id,
                    confirmacion   = CONF_PENDIENTE,
                    asistencia     = ASIST_PENDIENTE,
                )
                db.session.add(asist)
            creadas += 1

    db.session.commit()
    return creadas


# ------------------------------------------------------------------
# Vista principal — clases del mes
# ------------------------------------------------------------------
@asistencia_bp.route('/')
@login_required
@rol_requerido('admin', 'profesor')
def index():
    hoy   = date.today()
    anio  = request.args.get('anio',  hoy.year,  type=int)
    mes   = request.args.get('mes',   hoy.month, type=int)
    curso_id = request.args.get('curso_id', type=int)

    cursos = Curso.query.filter_by(activo=True).order_by(Curso.nombre).all()

    clases = []
    if curso_id:
        clases = (Clase.query
                  .filter_by(curso_id=curso_id)
                  .filter(db.extract('year',  Clase.fecha) == anio)
                  .filter(db.extract('month', Clase.fecha) == mes)
                  .order_by(Clase.fecha, Clase.hora_inicio)
                  .all())

    return render_template('asistencia/index.html',
                           cursos=cursos, clases=clases,
                           curso_id=curso_id, anio=anio, mes=mes,
                           hoy=hoy)


# ------------------------------------------------------------------
# Generar clases del mes (acción)
# ------------------------------------------------------------------
@asistencia_bp.route('/generar', methods=['POST'])
@login_required
@rol_requerido('admin')
def generar():
    curso_id = request.form.get('curso_id', type=int)
    anio     = request.form.get('anio',     type=int)
    mes      = request.form.get('mes',      type=int)

    if not all([curso_id, anio, mes]):
        flash('Datos incompletos.', 'danger')
        return redirect(url_for('asistencia.index'))

    n = generar_clases_mes(curso_id, anio, mes)
    if n:
        flash(f'{n} clase(s) generada(s) correctamente.', 'success')
    else:
        flash('No se generaron clases nuevas (ya existen o el curso no tiene horarios).', 'info')

    return redirect(url_for('asistencia.index',
                            curso_id=curso_id, anio=anio, mes=mes))


# ------------------------------------------------------------------
# Tomar lista de una clase
# ------------------------------------------------------------------
@asistencia_bp.route('/clase/<int:clase_id>', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin', 'profesor')
def tomar_lista(clase_id):
    clase = Clase.query.get_or_404(clase_id)

    if request.method == 'POST':
        for asist in clase.asistencias:
            valor = request.form.get(f'asist_{asist.id}')
            if not valor:
                continue

            asist.asistencia = valor

            # Si confirmó que iba y no asistió → deuda
            if (valor == ASIST_AUSENTE and
                    asist.confirmacion == CONF_SI and
                    not asist.deuda_generada):

                asist.deuda_generada = True
                deuda = DeudaAsistencia(
                    inscripcion_id = asist.inscripcion_id,
                    clase_id       = clase_id,
                    monto          = 0,  # el admin define el monto si aplica
                    pagado         = False,
                )
                db.session.add(deuda)

        clase.estado = CLASE_REALIZADA
        db.session.commit()
        flash('Asistencia registrada correctamente.', 'success')
        return redirect(url_for('asistencia.index',
                                curso_id=clase.curso_id,
                                anio=clase.fecha.year,
                                mes=clase.fecha.month))

    return render_template('asistencia/tomar_lista.html', clase=clase,
                           CONF_SI=CONF_SI, CONF_NO=CONF_NO,
                           ASIST_PRESENTE=ASIST_PRESENTE,
                           ASIST_AUSENTE=ASIST_AUSENTE,
                           ASIST_AUSENTE_DEUDA=ASIST_AUSENTE_DEUDA,
                           ASIST_JUSTIFICADO=ASIST_JUSTIFICADO)


# ------------------------------------------------------------------
# Cancelar clase
# ------------------------------------------------------------------
@asistencia_bp.route('/clase/<int:clase_id>/cancelar', methods=['POST'])
@login_required
@rol_requerido('admin')
def cancelar_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    clase.estado = CLASE_CANCELADA
    db.session.commit()
    flash(f'Clase del {clase.fecha.strftime("%d/%m/%Y")} cancelada.', 'info')
    return redirect(url_for('asistencia.index',
                            curso_id=clase.curso_id,
                            anio=clase.fecha.year,
                            mes=clase.fecha.month))


# ------------------------------------------------------------------
# Sync confirmaciones desde Google Sheets (llamado por N8N o manual)
# ------------------------------------------------------------------
@asistencia_bp.route('/sync-confirmaciones', methods=['POST'])
@login_required
@rol_requerido('admin')
def sync_confirmaciones():
    """
    Lee la hoja 'confirmaciones' de Sheets y actualiza el estado
    de confirmación de cada asistencia.
    Formato esperado en Sheets:
    alumno_id | clase_id | confirmacion (si/no) | timestamp
    """
    try:
        from app.sheets import leer_hoja
        registros = leer_hoja('confirmaciones')
        actualizados = 0

        for r in registros:
            alumno_id    = r.get('alumno_id')
            clase_id     = r.get('clase_id')
            confirmacion = str(r.get('confirmacion', '')).strip().lower()

            if not all([alumno_id, clase_id, confirmacion in ['si', 'no']]):
                continue

            asist = (Asistencia.query
                     .join(Inscripcion)
                     .filter(Inscripcion.alumno_id == alumno_id,
                             Asistencia.clase_id   == clase_id,
                             Asistencia.confirmacion == CONF_PENDIENTE)
                     .first())

            if asist:
                asist.confirmacion = CONF_SI if confirmacion == 'si' else CONF_NO
                actualizados += 1

        db.session.commit()
        flash(f'Sync completado: {actualizados} confirmaciones actualizadas.', 'success')

    except Exception as e:
        flash(f'Error al sincronizar: {str(e)}', 'danger')

    return redirect(url_for('asistencia.index'))


# ------------------------------------------------------------------
# Escribir clases próximas en Sheets (para que N8N dispare WA)
# ------------------------------------------------------------------
@asistencia_bp.route('/exportar-proximas', methods=['POST'])
@login_required
@rol_requerido('admin')
def exportar_proximas():
    """
    Escribe en 'clases_proximas' de Sheets las clases
    de las próximas 24hs que todavía no fueron notificadas.
    """
    try:
        from app.sheets import append_row
        ahora    = datetime.utcnow()
        limite   = ahora + timedelta(hours=24)
        hoy      = ahora.date()
        maniana  = limite.date()

        clases = (Clase.query
                  .filter(Clase.fecha.in_([hoy, maniana]),
                          Clase.estado == CLASE_PROGRAMADA)
                  .all())

        exportadas = 0
        for clase in clases:
            for asist in clase.asistencias:
                if asist.notificado:
                    continue
                alumno  = asist.inscripcion.alumno
                usuario = alumno.usuario
                append_row('clases_proximas', [
                    ahora.isoformat(),
                    clase.id,
                    clase.curso.nombre,
                    clase.fecha.isoformat(),
                    clase.hora_inicio,
                    alumno.id,
                    usuario.nombre,
                    alumno.telefono or '',
                    asist.id,
                    'pendiente',
                ])
                asist.notificado = True
                exportadas += 1

        db.session.commit()
        flash(f'{exportadas} notificaciones exportadas a Sheets.', 'success')

    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'danger')

    return redirect(url_for('asistencia.index'))


# ------------------------------------------------------------------
# Resumen de asistencia por alumno/mes (para liquidación)
# ------------------------------------------------------------------
@asistencia_bp.route('/resumen/<int:curso_id>/<int:anio>/<int:mes>')
@login_required
@rol_requerido('admin')
def resumen_mes(curso_id, anio, mes):
    curso = Curso.query.get_or_404(curso_id)

    clases = (Clase.query
              .filter_by(curso_id=curso_id)
              .filter(db.extract('year',  Clase.fecha) == anio)
              .filter(db.extract('month', Clase.fecha) == mes)
              .filter(Clase.estado != CLASE_CANCELADA)
              .all())

    total_clases = len(clases)

    resumen = []
    for inscripcion in curso.inscripciones:
        if not inscripcion.activo:
            continue

        presentes = sum(
            1 for c in clases
            for a in c.asistencias
            if a.inscripcion_id == inscripcion.id
            and a.asistencia == ASIST_PRESENTE
        )

        resumen.append({
            'alumno':        inscripcion.alumno.usuario.nombre,
            'inscripcion':   inscripcion,
            'presentes':     presentes,
            'total_clases':  total_clases,
            'porcentaje':    round(presentes / total_clases * 100) if total_clases else 0,
        })

    return render_template('asistencia/resumen_mes.html',
                           curso=curso, resumen=resumen,
                           anio=anio, mes=mes, total_clases=total_clases)
# ------------------------------------------------------------------
# Reprogramar clase completa (todos los alumnos)
# ------------------------------------------------------------------
@asistencia_bp.route('/clase/<int:clase_id>/reprogramar', methods=['GET', 'POST'])
@login_required
@rol_requerido('admin')
def reprogramar_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)

    if request.method == 'POST':
        nueva_fecha_str = request.form.get('fecha_nueva')
        motivo         = request.form.get('motivo', '').strip()

        if not nueva_fecha_str:
            flash('Ingresá la nueva fecha.', 'danger')
            return redirect(url_for('asistencia.reprogramar_clase', clase_id=clase_id))

        from datetime import date as date_type
        nueva_fecha = date_type.fromisoformat(nueva_fecha_str)

        # Guardar fecha original si es la primera reprogramación
        if not clase.fecha_original:
            clase.fecha_original = clase.fecha

        clase.fecha         = nueva_fecha
        clase.reprogramada  = True
        clase.motivo_reprog = motivo or None

        # Resetear confirmaciones y notificaciones para nuevo ciclo N8N
        for asist in clase.asistencias:
            asist.confirmacion = CONF_PENDIENTE
            asist.asistencia   = ASIST_PENDIENTE
            asist.notificado   = False
            asist.deuda_generada = False

        db.session.commit()
        flash(f'Clase reprogramada al {nueva_fecha.strftime("%d/%m/%Y")}. '
              f'Se reiniciaron las confirmaciones para el nuevo ciclo.', 'success')

        return redirect(url_for('asistencia.index',
                                curso_id=clase.curso_id,
                                anio=nueva_fecha.year,
                                mes=nueva_fecha.month))

    return render_template('asistencia/reprogramar_clase.html', clase=clase)