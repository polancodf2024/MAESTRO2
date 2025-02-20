import streamlit as st
from pathlib import Path
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import csv
from datetime import datetime
import pytz
import paramiko

import toml
from pathlib import Path

# Leer configuraciones locales desde config.toml
config = toml.load(".streamlit/config.toml")

# Configuración del servidor y correo
SMTP_SERVER = st.secrets["smtp_server"]
SMTP_PORT = st.secrets["smtp_port"]
EMAIL_USER = st.secrets["email_user"]
EMAIL_PASSWORD = st.secrets["email_password"]
NOTIFICATION_EMAIL = st.secrets["notification_email"]
CSV_CONVOCATORIAS_FILE = st.secrets["csv_convocatorias_file"]
REMOTE_HOST = st.secrets["remote_host"]
REMOTE_USER = st.secrets["remote_user"]
REMOTE_PASSWORD = st.secrets["remote_password"]
REMOTE_PORT = st.secrets["remote_port"]
REMOTE_DIR = st.secrets["remote_dir"]
REMOTE_FILE = st.secrets["remote_file"]
LOCAL_FILE = st.secrets["local_file"]




# Función para registrar datos en CSV con el formato correcto
def registrar_convocatoria(nombre, correo, numero_economico):
    tz_mexico = pytz.timezone("America/Mexico_City")
    fecha_actual = datetime.now(tz_mexico)

    # Formato de fecha y hora como "2024-11-20 14:55:35"
    fecha_hora = fecha_actual.strftime("%Y-%m-%d %H:%M:%S")

    estado = "Activo"
    fecha_terminacion = ""

    # Encabezados y datos del registro
    encabezados = [
        "Fecha y Hora", "Nombre Completo", "Correo Electronico", 
        "Numero Economico", "Estado", "Fecha de Terminacion"
    ]
    datos = [
        fecha_hora, nombre, correo, numero_economico, estado, fecha_terminacion
    ]

    # Guardar en el archivo CSV
    try:
        with open(LOCAL_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if file.tell() == 0:  # Si el archivo está vacío, escribe los encabezados
                writer.writerow(encabezados)
            writer.writerow(datos)
        subir_archivo_remoto()
    except Exception as e:
        st.error(f"Error al registrar convocatoria: {e}")

# Función para desuscribir a un usuario
def desuscribir_convocatoria(correo):
    try:
        # Leer los datos actuales del archivo CSV
        registros = []
        desuscrito = False
        with open(LOCAL_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            encabezados = next(reader)  # Guardar encabezados
            for row in reader:
                if row[2] == correo:  # Comparar el correo
                    row[4] = "Inactivo"  # Cambiar estado a "Inactivo"
                    row[5] = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")  # Fecha de terminación
                    desuscrito = True
                registros.append(row)

        # Escribir los datos actualizados de nuevo en el archivo CSV
        with open(LOCAL_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(encabezados)
            writer.writerows(registros)

        if desuscrito:
            subir_archivo_remoto()
            enviar_confirmacion_desuscripcion(correo)
            st.success("Has sido desuscrito exitosamente.")
        else:
            st.error("Correo no encontrado.")
    except Exception as e:
        st.error(f"Error al desuscribirse: {e}")

# Función para subir archivo remotamente
def subir_archivo_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_FILE, f"{REMOTE_DIR}/{REMOTE_FILE}")
        sftp.close()
        ssh.close()
        st.info("Archivo actualizado remotamente.")
    except Exception as e:
        st.error(f"Error al subir el archivo remotamente: {e}")

# Función para enviar confirmación de desuscripción
def enviar_confirmacion_desuscripcion(correo):
    try:
        mensaje = MIMEMultipart()
        mensaje['From'] = EMAIL_USER
        mensaje['To'] = correo
        mensaje['Subject'] = "Confirmación de desuscripción"

        cuerpo = "Has sido desuscrito exitosamente de las convocatorias."
        mensaje.attach(MIMEText(cuerpo, 'plain'))

        # Enviar correo
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, correo, mensaje.as_string())
    except Exception as e:
        st.error(f"Error al enviar confirmación de desuscripción: {e}")

# Función para enviar confirmación al usuario
def enviar_confirmacion_usuario(correo, nombre):
    try:
        mensaje = MIMEMultipart()
        mensaje['From'] = EMAIL_USER
        mensaje['To'] = correo
        mensaje['Subject'] = "Confirmación de suscripción"

        cuerpo = (
            f"Hola {nombre},\n\nTu suscripción ha sido recibida exitosamente. Gracias por participar.\n\nSaludos cordiales."
        )
        mensaje.attach(MIMEText(cuerpo, 'plain'))

        # Enviar correo
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, correo, mensaje.as_string())
    except Exception as e:
        st.error(f"Error al enviar confirmación al usuario: {e}")

# Añadir logo y título
st.image("escudo_COLOR.jpg", width=200)
st.title("Registro Para Recibir Convocatorias")

# Menú principal
opcion = st.radio("Seleccione una opción", ["Inscribirse", "Desuscribirse"])

if opcion == "Inscribirse":
    # Solicitar información del usuario
    nombre_completo = st.text_input("Nombre completo")
    correo_electronico = st.text_input("Correo Electrónico")
    correo_electronico_confirmacion = st.text_input("Confirma tu Correo Electrónico")
    numero_economico = st.text_input("Número Económico")

    # Procesar envío
    if st.button("Enviar"):
        if not nombre_completo or not correo_electronico or not correo_electronico_confirmacion or not numero_economico:
            st.error("Por favor, completa todos los campos correctamente.")
        elif correo_electronico != correo_electronico_confirmacion:
            st.error("Los correos electrónicos no coinciden.")
        else:
            with st.spinner("Registrando..."):
                # Registrar en el archivo CSV
                registrar_convocatoria(nombre_completo, correo_electronico, numero_economico)

                # Enviar confirmación al usuario
                enviar_confirmacion_usuario(correo_electronico, nombre_completo)

                st.success("Registro exitoso, confirmación enviada y archivo actualizado remotamente.")

elif opcion == "Desuscribirse":
    correo_desuscripcion = st.text_input("Correo Electrónico")
    if st.button("Desuscribirse"):
        if not correo_desuscripcion:
            st.error("Por favor, ingresa tu correo electrónico.")
        else:
            desuscribir_convocatoria(correo_desuscripcion)

