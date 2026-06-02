import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import (Usuario, Alumno, Profesor,
                        ROL_ADMIN, ROL_PROFESOR, ROL_ALUMNO,
                        CuentaCaja)

app = create_app()

def seed():
    with app.app_context():
        db.create_all()
        print("Tablas verificadas/creadas.")

        # Admin
        if not Usuario.query.filter_by(username='admin').first():
            u = Usuario(username='admin', nombre='Admin Eiren', rol=ROL_ADMIN, activo=True)
            u.set_password('admin1234')
            db.session.add(u)
            print("Admin creado  →  usuario: admin  /  clave: admin1234")
        else:
            print("Admin ya existe.")

        # Profesor demo
        if not Usuario.query.filter_by(username='profe.demo').first():
            u = Usuario(username='profe.demo', nombre='Profesor Demo', rol=ROL_PROFESOR, activo=True)
            u.set_password('profe1234')
            db.session.add(u)
            db.session.flush()
            db.session.add(Profesor(usuario_id=u.id, dni='20000001',
                                    telefono='3804000001', condicion_pago='por cuota'))
            print("Profesor creado  →  usuario: profe.demo  /  clave: profe1234")
        else:
            print("Profesor ya existe.")

        # Alumno demo
        if not Usuario.query.filter_by(username='alumno.demo').first():
            u = Usuario(username='alumno.demo', nombre='Alumno Demo', rol=ROL_ALUMNO, activo=True)
            u.set_password('alumno1234')
            db.session.add(u)
            db.session.flush()
            db.session.add(Alumno(usuario_id=u.id, dni='30000001', telefono='3804000002'))
            print("Alumno creado  →  usuario: alumno.demo  /  clave: alumno1234")
        else:
            print("Alumno ya existe.")

        # Cuentas de caja
        for nombre in ['efectivo', 'transferencia', 'otro']:
            if not CuentaCaja.query.filter_by(nombre=nombre).first():
                db.session.add(CuentaCaja(nombre=nombre, saldo_inicial=0, activo=True))
                print(f"Cuenta '{nombre}' creada.")
            else:
                print(f"Cuenta '{nombre}' ya existe.")

        db.session.commit()
        print()
        print("=" * 45)
        print("  admin        / admin1234")
        print("  profe.demo   / profe1234")
        print("  alumno.demo  / alumno1234")
        print("=" * 45)
        print("Cambiá las claves antes de producción.")

if __name__ == '__main__':
    seed()