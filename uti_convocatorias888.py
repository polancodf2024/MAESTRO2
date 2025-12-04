import streamlit as st
import pandas as pd
import paramiko
from pathlib import Path
import smtplib
import ssl
import time
import io

# Configuración de correo desde secrets.toml
SMTP_SERVER = st.secrets["smtp_server"]
SMTP_PORT = st.secrets["smtp_port"]
EMAIL_USER = st.secrets["email_user"]
EMAIL_PASSWORD = st.secrets["email_password"]
NOTIFICATION_EMAIL = st.secrets["notification_email"]

# Archivos CSV locales y remotos desde secrets.toml
CSV_CONVOCATORIAS_FILE = st.secrets["csv_convocatorias_file"]
LOCAL_FILE_CSV = st.secrets["local_file"]
LOCAL_FILE_PDF = st.secrets["local_file_pdf"]

# Configuración SFTP desde secrets.toml
REMOTE_HOST = st.secrets["remote_host"]
REMOTE_USER = st.secrets["remote_user"]
REMOTE_PASSWORD = st.secrets["remote_password"]
REMOTE_PORT = st.secrets["remote_port"]
REMOTE_DIR = st.secrets["remote_dir"]

# Archivos remotos desde secrets.toml
REMOTE_FILE_CSV = st.secrets["remote_file"]
REMOTE_FILE_PDF = st.secrets["remote_file_pdf"]

# Correo específico para contador de convocatorias
CONVOCATORIA_EMAIL = "abcdf2024dfabc@gmail.com"

# Configuración de delays
PAUSA_ENTRE_CORREOS = 2
PAUSA_ENTRE_GRUPOS = 10
GRUPO_SIZE = 5
TIMEOUT_SECONDS = 30

# Función para verificar la contraseña
def check_password():
    def password_entered():
        if st.session_state["password"] == REMOTE_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

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
    """Descarga archivo del servidor remoto"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.get(f"{REMOTE_DIR}/{file_remote}", file_local)
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        st.error(f"Error al descargar {file_remote}: {e}")
        return False

def enviar_archivo_remoto(file_local, file_remote):
    """Sube archivo al servidor remoto"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(file_local, f"{REMOTE_DIR}/{file_remote}")
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        st.error(f"Error al subir {file_remote}: {e}")
        return False

def leer_csv_directo_desde_remoto():
    """Lee el CSV directamente desde el servidor remoto (sin descargar)"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        
        # Leer el archivo directamente desde SFTP
        with sftp.file(f"{REMOTE_DIR}/{REMOTE_FILE_CSV}", 'r') as remote_file:
            content = remote_file.read().decode('utf-8')
        
        sftp.close()
        ssh.close()
        
        # Convertir a DataFrame
        df = pd.read_csv(io.StringIO(content))
        
        # Convertir columna numérica si existe
        if 'Numero economico' in df.columns:
            df['Numero economico'] = pd.to_numeric(df['Numero economico'], errors='coerce').astype('Int64')
        
        st.info(f"📄 CSV remoto cargado: {len(df)} registros")
        return df
        
    except Exception as e:
        st.error(f"❌ Error al leer CSV remoto: {e}")
        return None

def actualizar_csv_remoto(df):
    """Actualiza el CSV directamente en el servidor remoto"""
    try:
        # Convertir DataFrame a CSV en memoria
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_content = csv_buffer.getvalue()
        
        # Subir al servidor remoto
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        
        # Escribir directamente en el archivo remoto
        with sftp.file(f"{REMOTE_DIR}/{REMOTE_FILE_CSV}", 'w') as remote_file:
            remote_file.write(csv_content)
        
        sftp.close()
        ssh.close()
        
        return True
    except Exception as e:
        st.error(f"❌ Error al actualizar CSV remoto: {e}")
        return False

def send_email_with_attachment(email_recipient, subject, body, attachment_path):
    """Envía correo electrónico"""
    try:
        if not Path(attachment_path).exists():
            st.error(f"Archivo adjunto no encontrado: {attachment_path}")
            return False

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email_recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{Path(attachment_path).name}"')
            msg.attach(part)

        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=TIMEOUT_SECONDS) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        return True
        
    except Exception as e:
        st.error(f"Error enviando correo a {email_recipient}: {str(e)[:100]}")
        return False

def actualizar_contador_convocatorias(df):
    """Actualiza el contador de convocatorias en el CSV remoto"""
    try:
        # Buscar el correo específico de convocatorias
        correo_buscar = CONVOCATORIA_EMAIL.strip().lower()
        
        # Verificar que existe la columna
        if 'Correo electronico' not in df.columns:
            st.error("❌ Columna 'Correo electronico' no encontrada")
            return df
        
        # Crear columna normalizada para búsqueda
        df['correo_normalizado'] = df['Correo electronico'].astype(str).str.strip().str.lower()
        
        # Buscar el registro
        mask = df['correo_normalizado'] == correo_buscar
        registro_idx = df[mask].index
        
        if registro_idx.empty:
            # Crear nuevo registro
            nuevo_registro = pd.DataFrame([{
                'Fecha': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'Nombre completo': 'CONVOCATORIA',
                'Correo electronico': CONVOCATORIA_EMAIL,
                'Numero economico': 1,
                'Estado': 'Inactivo'
            }])
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            st.success("✅ Registro de convocatorias creado (contador: 1)")
        else:
            idx = registro_idx[0]
            current_value = df.at[idx, 'Numero economico']
            if pd.isna(current_value):
                current_value = 0
            new_value = int(current_value) + 1
            df.at[idx, 'Numero economico'] = new_value
            df.at[idx, 'Fecha'] = pd.Timestamp.now().strftime('%Y-%m-%d')  # Actualizar fecha
            st.success(f"🔢 Contador actualizado: {current_value} → {new_value}")
        
        # Eliminar columna temporal
        if 'correo_normalizado' in df.columns:
            df = df.drop(columns=['correo_normalizado'])
        
        return df
    except Exception as e:
        st.error(f"❌ Error al actualizar contador: {e}")
        return df

def enviar_convocatoria_a_activos():
    """Envía convocatoria a todos los contactos activos - TRABAJA DIRECTAMENTE CON EL REMOTO"""
    
    # 1. LEER CSV DIRECTAMENTE DEL SERVIDOR REMOTO
    st.info("📥 Leyendo CSV desde servidor remoto...")
    df = leer_csv_directo_desde_remoto()
    
    if df is None or df.empty:
        st.error("❌ No se pudo leer el CSV remoto o está vacío")
        return
    
    # 2. ACTUALIZAR CONTADOR EN EL CSV REMOTO
    df = actualizar_contador_convocatorias(df)
    
    # 3. GUARDAR CAMBIOS DIRECTAMENTE EN EL SERVIDOR REMOTO
    st.info("💾 Guardando cambios en servidor remoto...")
    if actualizar_csv_remoto(df):
        st.success("✅ CSV remoto actualizado exitosamente")
    else:
        st.error("❌ No se pudo actualizar el CSV remoto")
        return
    
    # 4. VERIFICAR COLUMNAS NECESARIAS
    required_cols = ['Correo electronico', 'Estado']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Columna '{col}' no encontrada en CSV remoto")
            return
    
    # 5. OBTENER CORREOS ACTIVOS DEL CSV REMOTO
    df['Estado'] = df['Estado'].astype(str).str.strip().str.lower()
    correos_activos = df[df['Estado'] == 'activo']['Correo electronico'].tolist()
    correos_activos = [str(c).strip() for c in correos_activos if pd.notna(c) and '@' in str(c)]
    
    if not correos_activos:
        st.warning("⚠️ No hay correos activos válidos en el CSV remoto")
        return
    
    # 6. VERIFICAR ARCHIVO PDF LOCAL
    if not Path(LOCAL_FILE_PDF).exists():
        st.error("❌ No hay archivo PDF local. Súbelo primero.")
        return
    
    # 7. INICIAR ENVÍO
    st.info(f"📨 Total de correos a enviar: {len(correos_activos)}")
    
    enviados = 0
    fallados = 0
    total_correos = len(correos_activos)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, correo in enumerate(correos_activos):
        status_text.text(f"Enviando a {correo[:30]}... ({i+1}/{total_correos})")
        
        if send_email_with_attachment(
            email_recipient=correo,
            subject="Nueva Convocatoria INCICh",
            body="Adjunto encontrarás la nueva convocatoria del INCICh. Revisa los detalles en el archivo PDF.",
            attachment_path=LOCAL_FILE_PDF
        ):
            enviados += 1
        else:
            fallados += 1
        
        progress_bar.progress((i + 1) / total_correos)
        
        # Pausa entre correos
        time.sleep(PAUSA_ENTRE_CORREOS)
        
        # Pausa más larga entre grupos
        if (i + 1) % GRUPO_SIZE == 0 and (i + 1) < total_correos:
            status_text.text(f"⏸️ Pausa de {PAUSA_ENTRE_GRUPOS} segundos...")
            time.sleep(PAUSA_ENTRE_GRUPOS)
    
    # 8. RESUMEN FINAL
    status_text.text("🎉 Proceso completado!")
    
    tasa_exito = (enviados/total_correos*100) if total_correos > 0 else 0
    st.success(f"""
    **📊 RESUMEN:**
    - 📨 Total procesados: {total_correos}
    - ✅ Envíos exitosos: {enviados}
    - ❌ Envíos fallidos: {fallados}
    - 📈 Tasa de éxito: {tasa_exito:.1f}%
    """)
    
    # 9. ENVIAR NOTIFICACIÓN
    if enviados > 0:
        try:
            send_email_with_attachment(
                email_recipient=NOTIFICATION_EMAIL,
                subject=f"Reporte Convocatorias - {pd.Timestamp.now().strftime('%Y-%m-%d')}",
                body=f"""Reporte de envío:
                
                - Total correos: {total_correos}
                - Éxitos: {enviados}
                - Fallos: {fallados}
                - Tasa éxito: {tasa_exito:.1f}%
                - Hora: {pd.Timestamp.now().strftime('%H:%M:%S')}
                """,
                attachment_path=LOCAL_FILE_PDF
            )
            st.info("📧 Reporte enviado")
        except:
            st.warning("⚠️ No se pudo enviar el reporte")

# Verificar contraseña
if not check_password():
    st.stop()

# Interfaz principal
st.image("escudo_COLOR.jpg", width=150)
st.title("📧 Sistema de Convocatorias INCICh")

# Sidebar
st.sidebar.header("⚙️ Configuración")
st.sidebar.info(f"""
**Parámetros:**
- ⏱️ Delay entre emails: {PAUSA_ENTRE_CORREOS}s
- 📦 Emails por bloque: {GRUPO_SIZE}
- ⏸️ Delay entre bloques: {PAUSA_ENTRE_GRUPOS}s
- ⏳ Timeout: {TIMEOUT_SECONDS}s
""")

# Sección para subir CSV AL SERVIDOR REMOTO
st.header("📤 Subir CSV al Servidor Remoto")
uploaded_csv = st.file_uploader("Selecciona archivo CSV para subir al servidor", type=["csv"])
if uploaded_csv is not None:
    # Guardar temporalmente localmente
    with open(LOCAL_FILE_CSV, "wb") as f:
        f.write(uploaded_csv.getbuffer())
    
    # Subir directamente al servidor remoto
    if enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV):
        st.success("✅ CSV subido exitosamente al servidor remoto")
    
    # Opcional: mostrar vista previa del CSV subido
    try:
        df_preview = pd.read_csv(LOCAL_FILE_CSV, encoding='utf-8')
        st.info(f"CSV contiene: {len(df_preview)} registros")
    except:
        pass

# Sección para descargar CSV DEL SERVIDOR REMOTO
st.header("📥 Descargar CSV del Servidor Remoto")
if st.button("💾 Descargar CSV Remoto"):
    if recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV):
        with open(LOCAL_FILE_CSV, "rb") as f:
            st.download_button(
                label="⬇️ Descargar CSV Remoto",
                data=f,
                file_name=REMOTE_FILE_CSV,
                mime="text/csv"
            )
    else:
        st.error("❌ No se pudo descargar el CSV remoto")

# Sección para subir PDF AL SERVIDOR REMOTO
st.header("📄 Subir Convocatoria PDF al Servidor Remoto")
uploaded_pdf = st.file_uploader("Subir PDF de convocatoria al servidor", type=["pdf"])
if uploaded_pdf is not None:
    # Guardar temporalmente localmente
    with open(LOCAL_FILE_PDF, "wb") as f:
        f.write(uploaded_pdf.getbuffer())
    
    file_size = Path(LOCAL_FILE_PDF).stat().st_size
    st.info(f"PDF tamaño: {file_size/1024:.1f} KB")
    
    # Subir directamente al servidor remoto
    if enviar_archivo_remoto(LOCAL_FILE_PDF, REMOTE_FILE_PDF):
        st.success("✅ PDF subido exitosamente al servidor remoto")

# Envío masivo - SIEMPRE TRABAJA CON EL REMOTO
st.header("🚀 Envío Masivo desde Servidor Remoto")
if st.button("📨 INICIAR ENVÍO MASIVO DESDE REMOTO", type="primary", use_container_width=True):
    # Verificar que existe el PDF local (necesario para adjuntar)
    if not Path(LOCAL_FILE_PDF).exists():
        st.error("❌ Primero sube un archivo PDF")
    else:
        with st.spinner("🚀 Iniciando envío masivo desde servidor remoto..."):
            enviar_convocatoria_a_activos()

# Pie de página
st.markdown("---")
st.caption(f"© {pd.Timestamp.now().year} - Sistema de Convocatorias INCICh - Trabajando con servidor remoto")
