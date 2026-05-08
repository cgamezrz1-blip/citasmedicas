"""
Script para poblar CitasMedicas con datos de prueba realistas.
Ejecutar en el Codespace: python3 poblar_db.py
"""
import sqlite3
import bcrypt
from datetime import datetime, date, timedelta
import random

DB_PATH = "citasmedicas.db"

def hash_pass(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("🏥 Poblando CitasMedicas con datos de prueba...")

# ── Especialidades (ya existen, verificar IDs) ─────────────────
c.execute("SELECT id, nombre FROM especialidades")
especialidades = {row[1]: row[0] for row in c.fetchall()}
print(f"✅ Especialidades: {list(especialidades.keys())}")

COLORES = ["#1a56db","#059669","#7c3aed","#d97706","#dc2626","#0891b2","#db2777","#65a30d"]

# ── 20 MÉDICOS ─────────────────────────────────────────────────
medicos = [
    # (nombre, email, especialidad, rethus, nacimiento)
    ("Dr. Carlos García López",      "carlos.garcia@citasmedicas.com",   "Cardiologia",       "RM-001234567", "1975-03-15"),
    ("Dra. Ana Martínez Ruiz",       "ana.martinez@citasmedicas.com",    "Ginecologia",       "RM-002345678", "1980-07-22"),
    ("Dr. Luis Pérez Sánchez",       "luis.perez@citasmedicas.com",      "Medicina General",  "RM-003456789", "1978-11-08"),
    ("Dra. María López Castro",      "maria.lopez@citasmedicas.com",     "Pediatria",         "RM-004567890", "1982-04-30"),
    ("Dr. Jorge Ramírez Torres",     "jorge.ramirez@citasmedicas.com",   "Ortopedia",         "RM-005678901", "1970-09-12"),
    ("Dra. Patricia Gómez Silva",    "patricia.gomez@citasmedicas.com",  "Dermatologia",      "RM-006789012", "1985-01-25"),
    ("Dr. Andrés Vargas Mora",       "andres.vargas@citasmedicas.com",   "Cardiologia",       "RM-007890123", "1973-06-18"),
    ("Dra. Claudia Herrera Díaz",    "claudia.herrera@citasmedicas.com", "Medicina General",  "RM-008901234", "1988-12-03"),
    ("Dr. Ricardo Mendoza Ríos",     "ricardo.mendoza@citasmedicas.com", "Ortopedia",         "RM-009012345", "1976-08-27"),
    ("Dra. Sandra Rojas Fuentes",    "sandra.rojas@citasmedicas.com",    "Ginecologia",       "RM-010123456", "1983-02-14"),
    ("Dr. Felipe Castro Mora",       "felipe.castro@citasmedicas.com",   "Dermatologia",      "RM-011234567", "1979-10-05"),
    ("Dra. Valentina Cruz Pinto",    "valentina.cruz@citasmedicas.com",  "Pediatria",         "RM-012345678", "1987-05-19"),
    ("Dr. Sebastián Morales León",   "sebastian.morales@citasmedicas.com","Cardiologia",      "RM-013456789", "1971-07-31"),
    ("Dra. Alejandra Reyes Vega",    "alejandra.reyes@citasmedicas.com", "Medicina General",  "RM-014567890", "1984-03-07"),
    ("Dr. Camilo Ortiz Navarro",     "camilo.ortiz@citasmedicas.com",    "Ortopedia",         "RM-015678901", "1977-11-22"),
    ("Dra. Isabella Jiménez Parra",  "isabella.jimenez@citasmedicas.com","Dermatologia",      "RM-016789012", "1986-09-16"),
    ("Dr. Mauricio Salinas Cano",    "mauricio.salinas@citasmedicas.com","Pediatria",         "RM-017890123", "1974-04-28"),
    ("Dra. Natalia Guerrero Hoyos",  "natalia.guerrero@citasmedicas.com","Ginecologia",       "RM-018901234", "1981-08-11"),
    ("Dr. Diego Pineda Ramos",       "diego.pineda@citasmedicas.com",    "Medicina General",  "RM-019012345", "1989-01-09"),
    ("Dra. Catalina Bermúdez Arce",  "catalina.bermudez@citasmedicas.com","Cardiologia",      "RM-020123456", "1972-06-24"),
]

medico_ids = []
medico_perfil_ids = []

for nombre, email, esp, rethus, nacimiento in medicos:
    color = random.choice(COLORES)
    try:
        c.execute("""INSERT INTO usuarios 
            (nombre, email, password, rol, activo, aprobado, fecha_nacimiento, 
             color_avatar, pregunta_seguridad, respuesta_seguridad, creado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (nombre, email, hash_pass("Medico123!"), "medico", 1, 1,
             nacimiento, color,
             "¿Cuál es el nombre de tu primera mascota?", "firulais",
             datetime.now().isoformat()))
        uid = c.lastrowid
        esp_id = especialidades.get(esp, 1)
        c.execute("""INSERT INTO medico_perfiles 
            (usuario_id, especialidad_id, numero_rethus, tarifa_consulta)
            VALUES (?,?,?,?)""", (uid, esp_id, rethus, 0.0))
        perfil_id = c.lastrowid
        medico_ids.append(uid)
        medico_perfil_ids.append(perfil_id)
        print(f"  ✅ Médico: {nombre} ({esp})")
    except Exception as e:
        print(f"  ⚠️ {nombre}: {e}")

# ── 40 PACIENTES ───────────────────────────────────────────────
pacientes_data = [
    ("Juan Pablo Rodríguez",    "juan.rodriguez@gmail.com",    "1990-05-14"),
    ("Laura Sofía Mendoza",     "laura.mendoza@gmail.com",     "1995-08-23"),
    ("Andrés Felipe Gómez",     "andres.gomez@gmail.com",      "1988-12-01"),
    ("Valentina Torres",         "valentina.torres@gmail.com",  "1992-03-17"),
    ("Santiago Ramírez",         "santiago.ramirez@gmail.com",  "1985-07-09"),
    ("Isabella García",          "isabella.garcia@gmail.com",   "1998-11-28"),
    ("Mateo Sánchez López",     "mateo.sanchez@gmail.com",     "1993-04-05"),
    ("Camila Herrera",           "camila.herrera@gmail.com",    "1991-09-30"),
    ("Sebastián Moreno",         "sebastian.moreno@gmail.com",  "1987-02-19"),
    ("Daniela Vargas",           "daniela.vargas@gmail.com",    "1996-06-12"),
    ("Miguel Ángel Castro",      "miguel.castro@gmail.com",     "1983-10-25"),
    ("Natalia Reyes",            "natalia.reyes@gmail.com",     "1994-01-08"),
    ("Julián Ortiz",             "julian.ortiz@gmail.com",      "1989-08-16"),
    ("Ana María Jiménez",        "ana.jimenez@gmail.com",       "1997-04-03"),
    ("Diego Alejandro Pinto",    "diego.pinto@gmail.com",       "1986-12-20"),
    ("Mariana Salinas",          "mariana.salinas@gmail.com",   "1999-07-14"),
    ("Carlos Eduardo Guerrero",  "carlos.guerrero@gmail.com",   "1984-03-27"),
    ("Sofía Bermúdez",           "sofia.bermudez@gmail.com",    "1993-11-05"),
    ("Felipe Andrés Pineda",     "felipe.pineda@gmail.com",     "1990-06-18"),
    ("Luisa Fernanda Cano",      "luisa.cano@gmail.com",        "1995-02-24"),
    ("Ricardo José Arce",        "ricardo.arce@gmail.com",      "1982-09-11"),
    ("Paola Andrea Hoyos",       "paola.hoyos@gmail.com",       "1991-05-30"),
    ("Alejandro Ramos",          "alejandro.ramos@gmail.com",   "1988-01-15"),
    ("Gloria Patricia León",     "gloria.leon@gmail.com",       "1975-08-07"),
    ("Tomás Esteban Parra",      "tomas.parra@gmail.com",       "1996-12-22"),
    ("Verónica Fuentes",         "veronica.fuentes@gmail.com",  "1984-04-10"),
    ("Esteban Mora Vega",        "esteban.mora@gmail.com",      "1992-10-03"),
    ("Carolina Silva Díaz",      "carolina.silva@gmail.com",    "1997-07-28"),
    ("Nicolás Pedraza",          "nicolas.pedraza@gmail.com",   "1986-03-15"),
    ("Andrea Montoya",           "andrea.montoya@gmail.com",    "1993-09-20"),
    ("Hernán Darío Ríos",        "hernan.rios@gmail.com",       "1979-11-08"),
    ("Catalina López",           "catalina.lopez2@gmail.com",   "1994-06-25"),
    ("Mauricio Estrada",         "mauricio.estrada@gmail.com",  "1987-02-12"),
    ("Adriana Córdoba",          "adriana.cordoba@gmail.com",   "1998-08-04"),
    ("Pablo Andrés Nieto",       "pablo.nieto@gmail.com",       "1981-05-19"),
    ("Diana Marcela Ospina",     "diana.ospina@gmail.com",      "1995-01-31"),
    ("Jairo Enrique Bernal",     "jairo.bernal@gmail.com",      "1976-10-16"),
    ("Lina María Castillo",      "lina.castillo@gmail.com",     "1992-07-07"),
    ("Gustavo Adolfo Prado",     "gustavo.prado@gmail.com",     "1989-04-23"),
    ("Yolanda Patricia Mejía",   "yolanda.mejia@gmail.com",     "1970-12-09"),
]

paciente_ids = []
for nombre, email, nacimiento in pacientes_data:
    color = random.choice(COLORES)
    try:
        c.execute("""INSERT INTO usuarios
            (nombre, email, password, rol, activo, aprobado, fecha_nacimiento,
             color_avatar, pregunta_seguridad, respuesta_seguridad, creado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (nombre, email, hash_pass("Paciente123!"), "paciente", 1, 1,
             nacimiento, color,
             "¿En qué ciudad naciste?", "bogota",
             datetime.now().isoformat()))
        paciente_ids.append(c.lastrowid)
        print(f"  ✅ Paciente: {nombre}")
    except Exception as e:
        print(f"  ⚠️ {nombre}: {e}")

conn.commit()

# ── CITAS ──────────────────────────────────────────────────────
print("\n📅 Creando citas...")

TARIFAS = {
    "Medicina General": 35000, "Pediatria": 55000, "Cardiologia": 120000,
    "Dermatologia": 90000, "Ginecologia": 100000, "Ortopedia": 110000
}
MOTIVOS = {
    "Medicina General":  ["Consulta general", "Control de tensión", "Fiebre", "Dolor de cabeza", "Revisión general"],
    "Pediatria":         ["Control de crecimiento", "Vacunación", "Fiebre en niños", "Control nutricional"],
    "Cardiologia":       ["Dolor en el pecho", "Palpitaciones", "Control de presión", "Electrocardiograma"],
    "Dermatologia":      ["Acné", "Manchas en la piel", "Alergia cutánea", "Revisión de lunares"],
    "Ginecologia":       ["Control prenatal", "Papanicolau", "Dolor menstrual", "Planificación familiar"],
    "Ortopedia":         ["Dolor de espalda", "Lesión deportiva", "Fractura", "Dolor articular"],
}
HORAS = ["08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30",
         "14:00","14:30","15:00","15:30","16:00","16:30","17:00"]
ESTADOS = ["pendiente","pendiente","confirmada","confirmada","confirmada","cancelada"]

hoy = date.today()
citas_creadas = 0
horas_usadas = {}  # {(medico_id, fecha, hora): True}

for i in range(120):
    pac_id = random.choice(paciente_ids)
    mp_idx = random.randint(0, len(medico_perfil_ids)-1)
    mp_id = medico_perfil_ids[mp_idx]

    # Fechas: mezcla de pasadas y futuras
    dias_offset = random.randint(-30, 45)
    fecha = (hoy + timedelta(days=dias_offset)).isoformat()
    hora = random.choice(HORAS)

    # Evitar doble reserva
    key = (mp_id, fecha, hora)
    if key in horas_usadas:
        continue
    horas_usadas[key] = True

    # Obtener especialidad del médico
    c.execute("SELECT e.nombre FROM medico_perfiles mp JOIN especialidades e ON mp.especialidad_id = e.id WHERE mp.id = ?", (mp_id,))
    row = c.fetchone()
    esp_nombre = row[0] if row else "Medicina General"

    motivo = random.choice(MOTIVOS.get(esp_nombre, ["Consulta general"]))
    costo = TARIFAS.get(esp_nombre, 35000)

    # Estado según fecha
    if dias_offset < -2:
        estado = random.choice(["confirmada","confirmada","cancelada"])
    elif dias_offset < 0:
        estado = random.choice(["confirmada","pendiente"])
    else:
        estado = random.choice(["pendiente","pendiente","confirmada"])

    cancelado_en = datetime.now().isoformat() if estado == "cancelada" else None

    try:
        c.execute("""INSERT INTO citas
            (paciente_id, medico_id, fecha, hora, motivo, estado, costo, creado_en, cancelado_en)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (pac_id, mp_id, fecha, hora, motivo, estado, costo,
             datetime.now().isoformat(), cancelado_en))
        cita_id = c.lastrowid

        # Notificacion
        c.execute("""INSERT INTO notificaciones
            (usuario_id, cita_id, tipo, mensaje, leida, creado_en)
            VALUES (?,?,?,?,?,?)""",
            (pac_id, cita_id, "confirmacion",
             f"Cita agendada para el {fecha} a las {hora}",
             random.choice([0,0,1]),
             datetime.now().isoformat()))
        citas_creadas += 1
    except Exception as e:
        pass

conn.commit()
conn.close()

print(f"\n🎉 ¡Base de datos poblada exitosamente!")
print(f"   👨‍⚕️ Médicos creados:   {len(medico_ids)}")
print(f"   🙋 Pacientes creados: {len(paciente_ids)}")
print(f"   📅 Citas creadas:     {citas_creadas}")
print(f"\n🔑 Credenciales:")
print(f"   Admin:    admin@citasmedicas.com / Admin123!")
print(f"   Médicos:  [email] / Medico123!")
print(f"   Pacientes:[email] / Paciente123!")
