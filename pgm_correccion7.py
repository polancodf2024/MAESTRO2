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
from datetime import datetime
import pytz
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
remote_password = st.secrets["remote_password"]
remote_port = st.secrets["remote_port"]
remote_dir = st.secrets["remote_dir"]
REMOTE_FILE = "REMOTE FILE"
LOCAL_FILE = "LOCAL_FILE"



# Función para descargar archivo remoto
def recibir_archivo_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{REMOTE_FILE}", LOCAL_FILE)
        sftp.close()
        ssh.close()
        print("Archivo sincronizado correctamente.")
    except Exception as e:
        st.error("Error al sincronizar con el servidor remoto.")
        st.error(str(e))

# Función para subir archivo al servidor remoto
def enviar_archivo_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_FILE, f"{remote_dir}/{REMOTE_FILE}")
        sftp.close()
        ssh.close()
        print("Archivo subido al servidor remoto.")
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

    # Adjuntar el archivo
    try:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={Path(attachment_path).name}')
            mensaje.attach(part)
    except Exception as e:
        print(f"Error al adjuntar el archivo: {e}")

    # Enviar el correo
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(email_user, email_password)
        server.sendmail(email_user, email_recipient, mensaje.as_string())

# Sincronización automática del archivo remoto al inicio
try:
    st.info("Sincronizando archivo con el servidor remoto...")
    recibir_archivo_remoto()
except Exception as e:
    st.error("Error al sincronizar automáticamente el archivo.")
    st.stop()

# Mostrar logo y título
st.image("escudo_COLOR.jpg", width=150)
st.title("Revisión de Artículos Científicos")

# Solicitar información del usuario
nombre_completo = st.text_input("Nombre completo del autor")
email = st.text_input("Correo electrónico del autor")
email_confirmacion = st.text_input("Confirma tu correo electrónico")
numero_economico = st.text_input("Número económico del autor")

# Selección de servicios
servicios_solicitados = st.multiselect(
    "¿Qué servicios solicita?",
    ["Verificación de originalidad", "Parafraseo", "Reporte de similitudes", "Factor IA", "Revisión de estilo", "Traducción parcial"]
)

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo .doc o .docx", type=["doc", "docx"])

# Botón para enviar archivo
if st.button("Enviar archivo"):
    if not nombre_completo or not email or not email_confirmacion or email != email_confirmacion or not numero_economico or uploaded_file is None:
        st.error("Por favor, completa todos los campos correctamente.")
    else:
        with st.spinner("Procesando archivo, por favor espera..."):
            # Guardar archivo localmente
            file_name = uploaded_file.name
            with open(file_name, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Registrar transacción en el archivo CSV
            tz_mexico = pytz.timezone("America/Mexico_City")
            fecha_hora = datetime.now(tz_mexico).strftime("%Y-%m-%d %H:%M:%S")
            data = {
                "Nombre": [nombre_completo],
                "Email": [email],
                "Número Económico": [numero_economico],  # Añadido el campo de "Número Económico" después de "Email"
                "Fecha y Hora": [fecha_hora],
                "Nombre del Archivo": [file_name],
                "Servicios Solicitados": [", ".join(servicios_solicitados)],
                "Estado": ["Activo"],
                "Fecha Terminación": [""]
            }
            df = pd.DataFrame(data)

            try:
                existing_df = pd.read_csv(LOCAL_FILE) if Path(LOCAL_FILE).exists() else pd.DataFrame()
                updated_df = pd.concat([existing_df, df], ignore_index=True)
                updated_df.to_csv(LOCAL_FILE, index=False)
                enviar_archivo_remoto()  # Subir CSV actualizado al servidor

                # Enviar correos al usuario y al administrador con el archivo adjunto
                send_email_with_attachment(
                    email_recipient=email,
                    subject="Confirmación de recepción de documento",
                    body=f"Hola {nombre_completo},\n\nHemos recibido tu archivo: {file_name} y los siguientes servicios solicitados: {', '.join(servicios_solicitados)}.",
                    attachment_path=file_name
                )

                send_email_with_attachment(
                    email_recipient=notification_email,
                    subject="Nuevo archivo recibido",
                    body=f"Se ha recibido un archivo de {nombre_completo} ({email}).\nServicios solicitados: {', '.join(servicios_solicitados)}.",
                    attachment_path=file_name
                )

                st.success("Archivo subido y correos enviados correctamente.")
            except Exception as e:
                st.error("Error al procesar el archivo o enviar correos.")
                st.error(str(e))

