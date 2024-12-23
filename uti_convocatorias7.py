import streamlit as st
import pandas as pd
import paramiko
from pathlib import Path
import smtplib
import ssl
import toml

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


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
REMOTE_FILE_CSV = "remote_file_csv"
REMOTE_FILE_PDF = "remote_file_pdf"
LOCAL_FILE_CSV = "local_file_csv"
LOCAL_FILE_PDF = "local_file_pdf"



# Configuración de correo
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "abcdf2024dfabc@gmail.com"
EMAIL_PASSWORD = "hjdd gqaw vvpj hbsy"
NOTIFICATION_EMAIL = "polanco@unam.mx"

# Función para descargar archivo remoto
def recibir_archivo_remoto(file_remote, file_local):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.get(f"{REMOTE_DIR}/{file_remote}", file_local)
        sftp.close()
        ssh.close()
        st.success(f"{file_local} descargado exitosamente.")
    except Exception as e:
        st.error(f"Error al descargar {file_local} del servidor remoto: {e}")

# Función para subir archivo remoto
def enviar_archivo_remoto(file_local, file_remote):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(file_local, f"{REMOTE_DIR}/{file_remote}")
        sftp.close()
        ssh.close()
        st.success(f"{file_local} subido exitosamente al servidor remoto.")
    except Exception as e:
        st.error(f"Error al subir {file_local} al servidor remoto: {e}")

# Función para eliminar archivo remoto
def borrar_archivo_remoto(file_remote):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.remove(f"{REMOTE_DIR}/{file_remote}")
        sftp.close()
        ssh.close()
        st.success(f"{file_remote} eliminado exitosamente del servidor remoto.")
    except Exception as e:
        st.error(f"Error al eliminar {file_remote} del servidor remoto: {e}")

# Función para enviar correos con archivo adjunto
def send_email_with_attachment(email_recipient, subject, body, attachment_path):
    mensaje = MIMEMultipart()
    mensaje['From'] = EMAIL_USER
    mensaje['To'] = email_recipient
    mensaje['Subject'] = subject
    mensaje.attach(MIMEText(body, 'plain'))

    try:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={Path(attachment_path).name}')
            mensaje.attach(part)
    except Exception as e:
        st.error(f"Error al adjuntar el archivo: {e}")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, email_recipient, mensaje.as_string())

# Función para enviar convocatoria a todos los correos activos
def enviar_convocatoria_a_activos():
    try:
        # Leer correos activos desde el archivo local
        df = pd.read_csv(LOCAL_FILE_CSV)
        correos_activos = df[df['Estado'] == 'Activo']['Correo Electronico'].tolist()

        for correo in correos_activos:
            send_email_with_attachment(
                email_recipient=correo,
                subject="Nueva Convocatoria",
                body="Adjunto encontrarás la nueva convocatoria. Revisa los detalles en el archivo PDF.",
                attachment_path=LOCAL_FILE_PDF
            )
        st.success("Convocatoria enviada a todos los correos activos.")
    except Exception as e:
        st.error(f"Error al enviar la convocatoria: {e}")

# Mostrar el logo y título
st.image("escudo_COLOR.jpg", width=150)
st.title("Gestión de Convocatorias")

# Opción de subir archivo CSV
st.header("Subir registro_convocatorias.csv")
uploaded_csv = st.file_uploader("Selecciona el archivo CSV para subir", type=["csv"])
if uploaded_csv is not None:
    try:
        with open(LOCAL_FILE_CSV, "wb") as f:
            f.write(uploaded_csv.getbuffer())
        enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV)
    except Exception as e:
        st.error(f"Error al procesar el archivo CSV: {e}")

# Opción de descargar archivo CSV
st.header("Descargar registro_convocatorias.csv")
if st.button("Descargar Registro CSV"):
    try:
        recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV)
        with open(LOCAL_FILE_CSV, "rb") as file:
            st.download_button(
                label="Descargar Registro CSV",
                data=file,
                file_name="registro_convocatorias.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"Error al descargar el archivo CSV: {e}")

# Opción de subir archivo PDF
st.header("Subir Convocatoria PDF")
uploaded_pdf = st.file_uploader("Selecciona el archivo PDF para subir", type=["pdf"])
if uploaded_pdf is not None:
    try:
        with open(LOCAL_FILE_PDF, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        enviar_archivo_remoto(LOCAL_FILE_PDF, REMOTE_FILE_PDF)
    except Exception as e:
        st.error(f"Error al procesar el archivo PDF: {e}")

# Opción de borrar archivo PDF
st.header("Borrar Convocatoria PDF")
if st.button("Borrar Convocatoria PDF"):
    try:
        borrar_archivo_remoto(REMOTE_FILE_PDF)
    except Exception as e:
        st.error(f"Error al borrar el archivo PDF: {e}")

# Opción de enviar convocatoria
st.header("Enviar Convocatoria a Todos los Activos")
if st.button("Enviar Convocatoria"):
    try:
        enviar_convocatoria_a_activos()
    except Exception as e:
        st.error(f"Error al enviar la convocatoria: {e}")

