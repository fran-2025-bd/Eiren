from datetime import date
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import Alumno, Profesor, Usuario
from app.auth.routes import rol_requerido
from . import cumpleanios_bp


@cumpleanios_bp.route('/')
@login_required
@rol_requerido('admin')
def listado():
    mes = request.args.get('mes', type=int)
    hoy = date.today()

    # Alumnos con fecha de nacimiento
    query_alumnos = (Alumno.query
                     .join(Usuario)
                     .filter(Alumno.fecha_nacimiento != None)
                     .filter(Usuario.activo == True))

    # Profesores con fecha de nacimiento
    query_profes = (Profesor.query
                    .join(Usuario)
                    .filter(Profesor.fecha_nacimiento != None)
                    .filter(Usuario.activo == True))

    if mes:
        query_alumnos = query_alumnos.filter(
            db.extract('month', Alumno.fecha_nacimiento) == mes)
        query_profes = query_profes.filter(
            db.extract('month', Profesor.fecha_nacimiento) == mes)

    alumnos  = query_alumnos.all()
    profes   = query_profes.all()

    # Combinar y ordenar por día/mes
    personas = []
    for a in alumnos:
        personas.append({
            'nombre':   a.usuario.nombre,
            'tipo':     'alumno',
            'fecha':    a.fecha_nacimiento,
            'telefono': a.telefono or '—',
            'email':    a.email_contacto or '—',
            'mes':      a.fecha_nacimiento.month,
            'dia':      a.fecha_nacimiento.day,
            'cumple_hoy': (a.fecha_nacimiento.day == hoy.day and
                           a.fecha_nacimiento.month == hoy.month),
        })
    for p in profes:
        personas.append({
            'nombre':   p.usuario.nombre,
            'tipo':     'profesor',
            'fecha':    p.fecha_nacimiento,
            'telefono': p.telefono or '—',
            'email':    p.email_contacto or '—',
            'mes':      p.fecha_nacimiento.month,
            'dia':      p.fecha_nacimiento.day,
            'cumple_hoy': (p.fecha_nacimiento.day == hoy.day and
                           p.fecha_nacimiento.month == hoy.month),
        })

    personas.sort(key=lambda x: (x['mes'], x['dia']))

    return render_template('cumpleanios/listado.html',
                           personas=personas, mes=mes, hoy=hoy)


@cumpleanios_bp.route('/exportar-sheets', methods=['POST'])
@login_required
@rol_requerido('admin')
def exportar_sheets():
    """
    Exporta cumpleaños de los próximos 2 días a Google Sheets
    para que N8N dispare los saludos.
    """
    try:
        from app.sheets import append_row
        from datetime import timedelta

        hoy     = date.today()
        maniana = hoy + timedelta(days=1)
        fechas  = [hoy, maniana]

        alumnos = Alumno.query.join(Usuario).filter(
            Alumno.fecha_nacimiento != None,
            Usuario.activo == True
        ).all()
        profes = Profesor.query.join(Usuario).filter(
            Profesor.fecha_nacimiento != None,
            Usuario.activo == True
        ).all()

        exportados = 0
        for f in fechas:
            for a in alumnos:
                fn = a.fecha_nacimiento
                if fn.day == f.day and fn.month == f.month:
                    append_row('cumpleanios', [
                        f.isoformat(),
                        'alumno',
                        a.usuario.nombre,
                        a.telefono or '',
                        a.email_contacto or '',
                        fn.strftime('%d/%m'),
                        'pendiente',
                    ])
                    exportados += 1
            for p in profes:
                fn = p.fecha_nacimiento
                if fn.day == f.day and fn.month == f.month:
                    append_row('cumpleanios', [
                        f.isoformat(),
                        'profesor',
                        p.usuario.nombre,
                        p.telefono or '',
                        p.email_contacto or '',
                        fn.strftime('%d/%m'),
                        'pendiente',
                    ])
                    exportados += 1

        flash(f'{exportados} cumpleaños exportados a Sheets.', 'success')
    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'danger')

    return redirect(url_for('cumpleanios.listado'))


@cumpleanios_bp.route('/api/mes/<int:anio>/<int:mes>')
@login_required
def api_mes(anio, mes):
    """
    API JSON para el calendario — retorna cumpleaños del mes.
    Accesible por todos los roles.
    """
    alumnos = Alumno.query.join(Usuario).filter(
        Alumno.fecha_nacimiento != None,
        Usuario.activo == True,
        db.extract('month', Alumno.fecha_nacimiento) == mes
    ).all()

    profes = Profesor.query.join(Usuario).filter(
        Profesor.fecha_nacimiento != None,
        Usuario.activo == True,
        db.extract('month', Profesor.fecha_nacimiento) == mes
    ).all()

    resultado = []
    for a in alumnos:
        resultado.append({
            'dia':    a.fecha_nacimiento.day,
            'nombre': a.usuario.nombre,
            'tipo':   'alumno',
        })
    for p in profes:
        resultado.append({
            'dia':    p.fecha_nacimiento.day,
            'nombre': p.usuario.nombre,
            'tipo':   'profesor',
        })

    return jsonify(resultado)
