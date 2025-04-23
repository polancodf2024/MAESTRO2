import streamlit as st
import pandas as pd
import paramiko
from pathlib import Path
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import toml

# Leer configuraciones locales desde config.toml
config = toml.load(".streamlit/config.toml")

# Configuración del servidor y correo
smtp_server = st.secrets["smtp_server"]
smtp_port = st.secrets["smtp_port"]
email_user = st.secrets["email_user"]
email_password = st.secrets["email_password"]
notification_email = st.secrets["notification_email"]
remote_host = st.secrets["remote_host"]
remote_user = st.secrets["remote_user"]
remote_password = st.secrets["remote_password"]  # Esta es la contraseña que usaremos para autenticación
remote_port = st.secrets["remote_port"]
remote_dir = st.secrets["remote_dir"]
remote_file_cor = st.secrets["remote_file_cor"]
local_file_cor = st.secrets["local_file_cor"]

# Función para descargar el archivo del servidor remoto
def recibir_archivo_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{remote_file_cor}", local_file_cor)
        sftp.close()
        ssh.close()
        print("Sincronización automática exitosa.")
    except Exception as e:
        st.error("Error al descargar el archivo del servidor remoto.")
        st.error(str(e))

# Función para subir el archivo al servidor remoto
def enviar_archivo_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.put(local_file_cor, f"{remote_dir}/{remote_file_cor}")
        sftp.close()
        ssh.close()
        st.success("Archivo subido al servidor remoto.")
    except Exception as e:
        st.error("Error al subir el archivo al servidor remoto.")
        st.error(str(e))

# Función para enviar correos con archivo adjunto
def send_email_with_attachment(email_recipient, subject, body, attachment_path):
    mensaje = MIMEMultipart()
    mensaje['From'] = email_user
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
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(email_user, email_password)
        server.sendmail(email_user, email_recipient, mensaje.as_string())

# Sincronización automática al iniciar
try:
    st.info("Sincronizando archivo con el servidor remoto...")
    recibir_archivo_remoto()
except Exception as e:
    st.warning("No se pudo sincronizar el archivo automáticamente.")
    st.warning(str(e))

# Mostrar el logo y título
st.image("escudo_COLOR.jpg", width=150)
st.title("Subir el archivo: registro_correccion.csv")

# Solicitar contraseña al inicio (usando remote_password)
input_password = st.text_input("Ingresa la contraseña para acceder:", type="password")
if input_password != remote_password:
    st.error("Contraseña incorrecta. Por favor ingrese la contraseña válida.")
    st.stop()

# Subida de archivo
uploaded_csv = st.file_uploader("Selecciona el archivo para subir y reemplazar el existente", type=["csv"])
if uploaded_csv is not None:
    try:
        with open(local_file_cor, "wb") as f:
            f.write(uploaded_csv.getbuffer())

        # Subir al servidor remoto
        enviar_archivo_remoto()

        # Enviar correos al administrador y usuario
        send_email_with_attachment(
            email_recipient=notification_email,
            subject="Nuevo archivo subido al servidor",
            body="Se ha subido un nuevo archivo al servidor.",
            attachment_path=local_file_cor
        )
        st.success("Archivo subido y correo enviado al administrador.")
    except Exception as e:
        st.error("Error al procesar el archivo.")
        st.error(str(e))

# Título para la sección de descarga
st.title("Descargar el archivo: registro_correccion.csv")

# Botón para descargar el archivo local
if Path(local_file_cor).exists():
    with open(local_file_cor, "rb") as file:
        st.download_button(
            label="Descargar registro_correccion.csv",
            data=file,
            file_name="registro_correccion.csv",
            mime="text/csv"
        )
    st.success("Archivo listo para descargar.")
else:
    st.warning("El archivo local no existe. Sincroniza primero con el servidor.")
