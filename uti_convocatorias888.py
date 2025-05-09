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

# Leer configuraciones desde secrets
config = toml.load(".streamlit/config.toml")

# Configuración del servidor y correo desde secrets
SMTP_SERVER = st.secrets["smtp_server"]
SMTP_PORT = st.secrets["smtp_port"]
EMAIL_USER = st.secrets["email_user"]
EMAIL_PASSWORD = st.secrets["email_password"]
NOTIFICATION_EMAIL = st.secrets["notification_email"]
REMOTE_HOST = st.secrets["remote_host"]
REMOTE_USER = st.secrets["remote_user"]
REMOTE_PASSWORD = st.secrets["remote_password"]
REMOTE_PORT = st.secrets["remote_port"]
REMOTE_DIR = st.secrets["remote_dir"]
REMOTE_FILE = st.secrets["remote_file"]
LOCAL_FILE = st.secrets["local_file"]

# Nombres de archivos específicos para convocatorias
REMOTE_FILE_CSV = st.secrets["remote_file"]  # Usando el mismo archivo remoto
REMOTE_FILE_PDF = "convocatoria.pdf"         # Nombre fijo para el PDF
LOCAL_FILE_CSV = st.secrets["local_file"]   # Usando el mismo archivo local
LOCAL_FILE_PDF = "convocatoria.pdf"         # Nombre fijo para el PDF local

# Función para verificar la contraseña
def check_password():
    """Solicita la contraseña y verifica si es correcta."""
    def password_entered():
        """Verifica si la contraseña es correcta."""
        if st.session_state["password"] == REMOTE_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No almacenar la contraseña
        else:
            st.session_state["password_correct"] = False

    # Mostrar el campo de contraseña solo si no se ha autenticado
    if "password_correct" not in st.session_state:
        st.image("escudo_COLOR.jpg", width=150)
        st.title("Acceso al Sistema")
        st.text_input(
            "Ingrese la contraseña de acceso:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.image("escudo_COLOR.jpg", width=150)
        st.title("Acceso al Sistema")
        st.text_input(
            "Contraseña incorrecta. Intente nuevamente:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    return True

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

def leer_csv_remoto():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        
        with sftp.file(f"{REMOTE_DIR}/{REMOTE_FILE_CSV}", 'r') as remote_file:
            df = pd.read_csv(remote_file)
        
        sftp.close()
        ssh.close()
        
        # Convertir 'Numero economico' a tipo numérico explícitamente
        if 'Numero economico' in df.columns:
            df['Numero economico'] = pd.to_numeric(df['Numero economico'], errors='coerce').astype('Int64')
        
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo CSV remoto: {e}")
        return None

def actualizar_contador_convocatorias(df):
    try:
        # Buscar el registro específico
        registro = df[
            (df['Correo electronico'].str.strip().str.lower() == 'abcdf2024dfabc@gmail.com')
        ]
        
        if not registro.empty:
            idx = registro.index[0]
            try:
                # Obtener y actualizar el número económico
                current_value = df.at[idx, 'Numero economico']
                if pd.isna(current_value):
                    current_value = 0
                new_value = current_value + 1
                df.at[idx, 'Numero economico'] = new_value
                st.success(f"Contador actualizado: {current_value} → {new_value}")
            except Exception as e:
                st.warning(f"No se pudo actualizar el contador: {e}")
        else:
            st.warning("Registro de convocatorias no encontrado")
        
        return df
    except Exception as e:
        st.error(f"Error al actualizar contador: {e}")
        return df

def enviar_convocatoria_a_activos():
    try:
        # Leer y actualizar el archivo CSV
        df = leer_csv_remoto()
        if df is None:
            return
            
        # Actualizar contador primero
        df = actualizar_contador_convocatorias(df)
        
        # Guardar cambios
        with open(LOCAL_FILE_CSV, 'w') as f:
            df.to_csv(f, index=False)
        enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV)

        # Verificar columnas
        if len(df.columns) < 3:
            st.error("Error: El archivo CSV debe tener al menos 3 columnas")
            return

        columna_correo = df.columns[2]
        columna_estado = df.columns[-1]
        
        # Obtener correos activos
        correos_activos = df[df[columna_estado].str.strip().str.lower() == 'activo'][columna_correo].tolist()
        
        if not correos_activos:
            st.warning("No hay correos activos en el registro.")
            return

        if not Path(LOCAL_FILE_PDF).exists():
            st.error("Error: El archivo PDF local no existe. Por favor súbelo primero.")
            return

        # Enviar convocatorias
        enviados = 0
        for correo in correos_activos:
            if pd.notna(correo) and '@' in str(correo):
                try:
                    send_email_with_attachment(
                        email_recipient=correo.strip(),
                        subject="Nueva Convocatoria INCICh",
                        body="Adjunto encontrarás la nueva convocatoria del INCICh. Revisa los detalles en el archivo PDF.",
                        attachment_path=LOCAL_FILE_PDF
                    )
                    enviados += 1
                except Exception as e:
                    st.warning(f"Error al enviar a {correo}: {str(e)}")
        
        st.success(f"Convocatoria enviada a {enviados} de {len(correos_activos)} correos activos.")
    except Exception as e:
        st.error(f"Error al enviar la convocatoria: {e}")

# Verificar la contraseña al inicio
if not check_password():
    st.stop()

# Interfaz de usuario (solo se muestra si la contraseña es correcta)
st.image("escudo_COLOR.jpg", width=150)
st.title("Gestión de Convocatorias")

# Sección para subir archivo CSV
st.header(f"Subir {LOCAL_FILE_CSV}")
uploaded_csv = st.file_uploader("Selecciona el archivo CSV para subir", type=["csv"])
if uploaded_csv is not None:
    try:
        with open(LOCAL_FILE_CSV, "wb") as f:
            f.write(uploaded_csv.getbuffer())
        enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV)
    except Exception as e:
        st.error(f"Error al procesar el archivo CSV: {e}")

# Sección para descargar archivo CSV
st.header(f"Descargar {LOCAL_FILE_CSV}")
if st.button("Descargar Registro CSV"):
    try:
        recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV)
        with open(LOCAL_FILE_CSV, "rb") as file:
            st.download_button(
                label="Descargar Registro CSV",
                data=file,
                file_name=LOCAL_FILE_CSV,
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"Error al descargar el archivo CSV: {e}")

# Sección para subir archivo PDF
st.header("Subir Convocatoria PDF")
uploaded_pdf = st.file_uploader("Selecciona el archivo PDF para subir", type=["pdf"])
if uploaded_pdf is not None:
    try:
        with open(LOCAL_FILE_PDF, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        enviar_archivo_remoto(LOCAL_FILE_PDF, REMOTE_FILE_PDF)
    except Exception as e:
        st.error(f"Error al procesar el archivo PDF: {e}")

# Sección para borrar archivo PDF
st.header("Borrar Convocatoria PDF")
if st.button("Borrar Convocatoria PDF"):
    try:
        borrar_archivo_remoto(REMOTE_FILE_PDF)
    except Exception as e:
        st.error(f"Error al borrar el archivo PDF: {e}")

# Sección para enviar convocatorias
st.header("Enviar Convocatoria a Todos los Activos")
if st.button("Enviar Convocatoria"):
    enviar_convocatoria_a_activos()
