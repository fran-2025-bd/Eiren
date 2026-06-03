from datetime import date, timedelta
from flask import render_template, request, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import (Curso, HorarioCurso, Clase, Profesor,
                        DisponibilidadProfesor, CLASE_PROGRAMADA)
from app.auth.routes import rol_requerido
from . import agenda_bp

HORAS_GRILLA = [
    '07:00','08:00','09:00','10:00','11:00','12:00',
    '13:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00'
]

DIAS_SEMANA = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']

SALAS = ['sala_1', 'sala_2', 'sala_3']
SALA_LABELS = {'sala_1': 'Sala 1', 'sala_2': 'Sala 2', 'sala_3': 'Sala 3'}


def _lunes_de_semana(referencia=None):
    hoy = referencia or date.today()
    return hoy - timedelta(days=hoy.weekday())


def _dia_semana_str(fecha):
    return DIAS_SEMANA[fecha.weekday()]


def _horario_en_franja(hora_slot, hora_ini_slot, hora_fin_slot,
                        hora_ini_franja, hora_fin_franja):
    """Verifica si un slot horario se superpone con una franja."""
    return hora_ini_slot < hora_fin_franja and hora_fin_slot > hora_ini_franja


def _construir_datos_dia(fecha):
    """
    Para una fecha dada, construye los datos de cada sala y slot horario:
    - Si hay clase fija o reprogramada → ocupado
    - Si hay sala libre y profesores disponibles → libre
    - Si no hay disponibilidad ni clase → sin datos
    """
    dia_str = _dia_semana_str(fecha)
    resultado = {}

    # Clases del día (fijas y reprogramadas)
    clases_dia = (Clase.query
                  .filter_by(fecha=fecha)
                  .filter(Clase.estado != 'cancelada')
                  .all())

    # Disponibilidades de profesores para este día
    disponibilidades = (DisponibilidadProfesor.query
                        .filter_by(dia_semana=dia_str)
                        .all())

    # Cursos recurrentes con horario en este día
    horarios_recurrentes = (HorarioCurso.query
                            .filter_by(dia_semana=dia_str)
                            .join(Curso)
                            .filter(Curso.activo == True)
                            .all())

    for hora in HORAS_GRILLA:
        hora_fin_slot = f"{int(hora[:2])+1:02d}:{hora[3:]}"
        resultado[hora] = {}

        for sala_key in SALAS:
            sala_label = SALA_LABELS[sala_key]

            # 1. Buscar clase del día en esta sala y hora
            clase_en_slot = None
            for c in clases_dia:
                if (c.curso.sala == sala_key and
                    c.hora_inicio and c.hora_fin and
                    c.hora_inicio < hora_fin_slot and c.hora_fin > hora):
                    clase_en_slot = c
                    break

            if clase_en_slot:
                c = clase_en_slot
                resultado[hora][sala_label] = {
                    'tipo':       'reprog' if c.reprogramada else 'fijo',
                    'curso':      c.curso.nombre,
                    'prof':       c.curso.profesor.usuario.nombre,
                    'alumnos':    len(c.curso.alumnos_activos()),
                    'individual': c.curso.modalidad == 'individual',
                    'clase_id':   c.id,
                    'nota':       c.motivo_reprog or '',
                }
                continue

            # 2. Buscar horario recurrente en esta sala y hora
            horario_en_slot = None
            for h in horarios_recurrentes:
                if (h.curso.sala == sala_key and
                    h.hora_inicio < hora_fin_slot and h.hora_fin > hora):
                    horario_en_slot = h
                    break

            if horario_en_slot:
                h = horario_en_slot
                resultado[hora][sala_label] = {
                    'tipo':       'fijo',
                    'curso':      h.curso.nombre,
                    'prof':       h.curso.profesor.usuario.nombre,
                    'alumnos':    len(h.curso.alumnos_activos()),
                    'individual': h.curso.modalidad == 'individual',
                    'clase_id':   None,
                    'nota':       '',
                }
                continue

            # 3. Sala libre — buscar profesores disponibles
            profes_disponibles = []
            for d in disponibilidades:
                if d.hora_inicio < hora_fin_slot and d.hora_fin > hora:
                    # Verificar que el profesor no tenga otro curso en este horario
                    ocupado = False
                    for h2 in horarios_recurrentes:
                        if (h2.curso.profesor_id == d.profesor_id and
                            h2.hora_inicio < hora_fin_slot and h2.hora_fin > hora):
                            ocupado = True
                            break
                    if not ocupado:
                        for c2 in clases_dia:
                            if (c2.curso.profesor_id == d.profesor_id and
                                c2.hora_inicio and
                                c2.hora_inicio < hora_fin_slot and c2.hora_fin > hora):
                                ocupado = True
                                break
                    if not ocupado:
                        profes_disponibles.append(d.profesor.usuario.nombre)

            if profes_disponibles:
                resultado[hora][sala_label] = {
                    'tipo':   'libre',
                    'profes': list(set(profes_disponibles)),
                }
            else:
                resultado[hora][sala_label] = {'tipo': 'sin_disp'}

    return resultado


@agenda_bp.route('/')
@login_required
@rol_requerido('admin')
def index():
    semana_str = request.args.get('semana')
    if semana_str:
        try:
            ref = date.fromisoformat(semana_str)
            lunes = _lunes_de_semana(ref)
        except ValueError:
            lunes = _lunes_de_semana()
    else:
        lunes = _lunes_de_semana()

    dias = [lunes + timedelta(days=i) for i in range(7)]
    semana_anterior = (lunes - timedelta(weeks=1)).isoformat()
    semana_siguiente = (lunes + timedelta(weeks=1)).isoformat()

    # Datos del día activo (por defecto lunes o hoy si está en la semana)
    hoy = date.today()
    dia_activo = hoy if lunes <= hoy <= lunes + timedelta(days=6) else lunes
    datos_dia = _construir_datos_dia(dia_activo)

    return render_template('agenda/index.html',
                           dias=dias,
                           dia_activo=dia_activo,
                           datos_dia=datos_dia,
                           horas=HORAS_GRILLA,
                           salas=[SALA_LABELS[s] for s in SALAS],
                           semana_anterior=semana_anterior,
                           semana_siguiente=semana_siguiente,
                           hoy=hoy)


@agenda_bp.route('/dia/<fecha_str>')
@login_required
@rol_requerido('admin')
def datos_dia(fecha_str):
    """API JSON para cargar datos de un día sin recargar la página."""
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return jsonify({'error': 'fecha inválida'}), 400

    datos = _construir_datos_dia(fecha)
    return jsonify(datos)
