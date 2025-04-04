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
import csv
import re
import unicodedata
from typing import Optional

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
remote_file_cor = st.secrets["remote_file_cor"]
local_file_cor = st.secrets["local_file_cor"]

# Función para descargar archivo remoto
def recibir_archivo_remoto():
    """Descarga el archivo CSV desde el servidor remoto via SFTP."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{remote_file_cor}", local_file_cor)
        sftp.close()
        ssh.close()
        st.success("Archivo sincronizado correctamente con el servidor remoto.")
    except Exception as e:
        st.error("Error al sincronizar con el servidor remoto.")
        st.error(str(e))
        raise

# Función para subir archivo al servidor remoto
def enviar_archivo_remoto():
    """Sube el archivo CSV actualizado al servidor remoto via SFTP."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.put(local_file_cor, f"{remote_dir}/{remote_file_cor}")
        sftp.close()
        ssh.close()
        st.success("Archivo subido al servidor remoto correctamente.")
    except Exception as e:
        st.error("Error al subir el archivo al servidor remoto.")
        st.error(str(e))
        raise

def get_mime_type(filename: str) -> tuple:
    """Determina el tipo MIME correcto basado en la extensión del archivo."""
    file_extension = filename.split('.')[-1].lower()
    
    if file_extension == 'doc':
        return ('application', 'msword')
    elif file_extension == 'docx':
        return ('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document')
    else:
        return ('application', 'octet-stream')

def clean_filename(filename: str) -> str:
    """Limpia el nombre del archivo de caracteres especiales y normaliza."""
    # Normaliza caracteres unicode (ej: á → a)
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    # Elimina caracteres no permitidos
    filename = re.sub(r'[^\w\-_. ]', '', filename)
    return filename.strip()

# Función para enviar correos con archivo adjunto
def send_email_with_attachment(email_recipient: str, subject: str, body: str, attachment_path: str) -> bool:
    """
    Envía un correo electrónico con un archivo adjunto.
    
    Args:
        email_recipient: Dirección de correo del destinatario
        subject: Asunto del correo
        body: Cuerpo del mensaje
        attachment_path: Ruta al archivo a adjuntar
        
    Returns:
        bool: True si el correo se envió correctamente, False si hubo error
    """
    # Validar email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email_recipient):
        st.error(f"Dirección de correo inválida: {email_recipient}")
        return False

    mensaje = MIMEMultipart()
    mensaje['From'] = email_user
    mensaje['To'] = email_recipient
    mensaje['Subject'] = subject
    mensaje.attach(MIMEText(body, 'plain'))

    filename = clean_filename(Path(attachment_path).name)
    mime_type = get_mime_type(filename)

    try:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase(*mime_type)
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            
            # Codificación correcta del nombre del archivo
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename=filename
            )
            mensaje.attach(part)
    except Exception as e:
        st.error(f"Error al adjuntar el archivo: {e}")
        return False

    # Enviar el correo
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_user, email_password)
            server.sendmail(email_user, email_recipient, mensaje.as_string())
        return True
    except Exception as e:
        st.error(f"Error al enviar el correo: {e}")
        return False

# Validación de email
def is_valid_email(email: str) -> bool:
    """Valida que el formato del email sea correcto."""
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

# Sincronización automática del archivo remoto al inicio
try:
    st.info("Sincronizando archivo con el servidor remoto...")
    recibir_archivo_remoto()
except Exception as e:
    st.error("Error al sincronizar automáticamente el archivo.")
    st.stop()

# Mostrar logo y título
st.image("escudo_COLOR.jpg", width=150)
st.title("Revisión de artículos científicos")

# Solicitar información del usuario
nombre_completo = st.text_input("Nombre completo del autor")
email = st.text_input("Correo electrónico del autor")
email_confirmacion = st.text_input("Confirma tu correo electrónico")
numero_economico = st.text_input("Número económico del autor")
nombre_articulo = st.text_input("Título del artículo")

# Selección de servicios
servicios_solicitados = st.multiselect(
    "¿Qué servicios solicita?",
    ["Detección de plagio", "Detección de escritura hecha por IA", 
     "Corrección ortográfica y parafraseo en inglés", 
     "Corrección ortográfica y parafraseo en español"]
)

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo .doc o .docx", type=["doc", "docx"])

# Botón para enviar archivo
if st.button("Enviar archivo"):
    # Validación de campos
    errors = []
    if not nombre_completo:
        errors.append("Nombre completo es requerido")
    if not email:
        errors.append("Correo electrónico es requerido")
    elif not is_valid_email(email):
        errors.append("Correo electrónico no válido")
    if email != email_confirmacion:
        errors.append("Los correos electrónicos no coinciden")
    if not numero_economico:
        errors.append("Número económico es requerido")
    if not uploaded_file:
        errors.append("Debes subir un archivo")
    
    if errors:
        for error in errors:
            st.error(error)
    else:
        with st.spinner("Procesando archivo, por favor espera..."):
            # Guardar archivo localmente con nombre limpio
            original_filename = uploaded_file.name
            file_name = clean_filename(original_filename)
            with open(file_name, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Definir orden de columnas
            column_order = [
                "Nombre", 
                "Email", 
                "Número económico", 
                "Fecha", 
                "Nombre del archivo", 
                "Nombre del artículo", 
                "Servicios solicitados", 
                "Estado"
            ]

            # Registrar transacción en el archivo CSV
            tz_mexico = pytz.timezone("America/Mexico_City")
            fecha_hora = datetime.now(tz_mexico).strftime("%Y-%m-%d %H:%M:%S")
            data = {
                "Nombre": [nombre_completo],
                "Email": [email],
                "Número económico": [numero_economico],
                "Fecha": [fecha_hora],
                "Nombre del archivo": [file_name],
                "Nombre del artículo": [nombre_articulo],
                "Servicios solicitados": [", ".join(servicios_solicitados)],
                "Estado": ["Pendiente"]
            }

            # Crear DataFrame asegurando el orden de columnas
            df = pd.DataFrame(data, columns=column_order)

            try:
                # Leer archivo existente o crear uno nuevo con las columnas correctas
                existing_df = pd.read_csv(local_file_cor) if Path(local_file_cor).exists() else pd.DataFrame(columns=column_order)
                updated_df = pd.concat([existing_df, df], ignore_index=True)
                updated_df = updated_df[column_order]  # Asegurar el orden de columnas
                
                # Guardar el CSV con comillas para todos los campos
                updated_df.to_csv(local_file_cor, index=False, quoting=csv.QUOTE_ALL)
                
                # Subir CSV actualizado al servidor
                enviar_archivo_remoto()

                # Enviar correos al usuario y al administrador con el archivo adjunto
                email_sent_user = send_email_with_attachment(
                    email_recipient=email,
                    subject="Confirmación de recepción de documento",
                    body=f"Hola {nombre_completo},\n\nHemos recibido tu archivo: {file_name}\n\nServicios solicitados: {', '.join(servicios_solicitados)}\n\nFecha de recepción: {fecha_hora}",
                    attachment_path=file_name
                )

                email_sent_admin = send_email_with_attachment(
                    email_recipient=notification_email,
                    subject=f"Nuevo archivo recibido - {nombre_completo}",
                    body=f"Se ha recibido un nuevo archivo para revisión:\n\nAutor: {nombre_completo}\nEmail: {email}\nArchivo: {file_name}\nServicios solicitados: {', '.join(servicios_solicitados)}\nFecha: {fecha_hora}",
                    attachment_path=file_name
                )

                if email_sent_user and email_sent_admin:
                    st.success("""
                    ¡Archivo enviado correctamente!
                    
                    - Registro actualizado en el sistema
                    - Correo de confirmación enviado al autor
                    - Notificación enviada al administrador
                    """)
                else:
                    st.warning("""
                    El archivo se registró correctamente pero hubo problemas al enviar los correos.
                    Por favor contacta al administrador del sistema.
                    """)

            except Exception as e:
                st.error("Error al procesar la solicitud:")
                st.error(str(e))
                # Intentar eliminar el archivo temporal si hubo error
                try:
                    if Path(file_name).exists():
                        Path(file_name).unlink()
                except:
                    pass
