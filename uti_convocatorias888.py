import streamlit as st
import pandas as pd
import paramiko
from pathlib import Path
import smtplib
import ssl
import toml
import time
import io
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

# Configuración de delays y bloques para evitar detección como spam
DELAY_ENTRE_EMAILS = 3  # segundos entre cada email
DELAY_ENTRE_BLOQUES = 11  # segundos entre bloques de emails
EMAILS_POR_BLOQUE = 11  # cantidad de emails por bloque

# Variable global para la codificación del CSV
if 'csv_encoding' not in st.session_state:
    st.session_state.csv_encoding = "latin-1"

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
    """Descarga un archivo del servidor remoto."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.get(f"{REMOTE_DIR}/{file_remote}", file_local)
        sftp.close()
        ssh.close()
        st.success(f"{file_local} descargado exitosamente.")
        return True
    except Exception as e:
        st.error(f"Error al descargar {file_local} del servidor remoto: {e}")
        return False

def enviar_archivo_remoto(file_local, file_remote):
    """Sube un archivo al servidor remoto."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.put(file_local, f"{REMOTE_DIR}/{file_remote}")
        sftp.close()
        ssh.close()
        st.success(f"{file_local} subido exitosamente al servidor remoto.")
        return True
    except Exception as e:
        st.error(f"Error al subir {file_local} al servidor remoto: {e}")
        return False

def borrar_archivo_remoto(file_remote):
    """Elimina un archivo del servidor remoto."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.remove(f"{REMOTE_DIR}/{file_remote}")
        sftp.close()
        ssh.close()
        st.success(f"{file_remote} eliminado exitosamente del servidor remoto.")
        return True
    except Exception as e:
        st.error(f"Error al eliminar {file_remote} del servidor remoto: {e}")
        return False

def send_email_with_attachment(email_recipient, subject, body, attachment_path):
    """Envía un correo electrónico con archivo adjunto."""
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
        return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, email_recipient, mensaje.as_string())
        return True
    except Exception as e:
        st.error(f"Error al enviar el correo a {email_recipient}: {e}")
        return False

def detectar_codificacion_csv(ruta_archivo):
    """Detecta la codificación de un archivo CSV."""
    import chardet
    
    try:
        with open(ruta_archivo, 'rb') as f:
            resultado = chardet.detect(f.read(10000))  # Leer solo los primeros 10KB para mayor velocidad
        
        encoding = resultado['encoding']
        confianza = resultado['confidence']
        
        # Mapear algunas codificaciones comunes
        if encoding is None:
            encoding = 'latin-1'
        elif encoding.lower() == 'ascii':
            encoding = 'utf-8'
        elif encoding.lower() == 'windows-1252':
            encoding = 'cp1252'
        
        st.info(f"Codificación detectada: {encoding} (confianza: {confianza:.2%})")
        return encoding
    except:
        return 'latin-1'  # Valor por defecto para archivos en español

def leer_csv_remoto():
    """Lee el archivo CSV remoto con manejo de codificaciones."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASSWORD)
        sftp = ssh.open_sftp()
        
        # Opción 1: Descargar temporalmente y detectar codificación
        temp_file = "temp_csv_remote.csv"
        sftp.get(f"{REMOTE_DIR}/{REMOTE_FILE_CSV}", temp_file)
        
        # Obtener la codificación seleccionada por el usuario o detectarla
        if st.session_state.csv_encoding == "auto":
            encoding_usar = detectar_codificacion_csv(temp_file)
        else:
            encoding_usar = st.session_state.csv_encoding
        
        # Intentar leer con la codificación seleccionada
        try:
            df = pd.read_csv(temp_file, encoding=encoding_usar)
            st.success(f"Archivo CSV leído exitosamente con codificación: {encoding_usar}")
        except UnicodeDecodeError:
            # Si falla, intentar con Latin-1 como respaldo
            st.warning(f"Codificación {encoding_usar} falló, intentando con latin-1...")
            df = pd.read_csv(temp_file, encoding='latin-1')
        
        # Limpiar archivo temporal
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        sftp.close()
        ssh.close()
        
        # Convertir 'Numero economico' a tipo numérico explícitamente
        if 'Numero economico' in df.columns:
            df['Numero economico'] = pd.to_numeric(df['Numero economico'], errors='coerce').astype('Int64')
        
        # Mostrar información del archivo cargado
        st.info(f"Archivo CSV cargado: {len(df)} registros, {len(df.columns)} columnas")
        
        return df
        
    except FileNotFoundError as e:
        st.error(f"Archivo no encontrado en el servidor remoto: {REMOTE_FILE_CSV}")
        return None
    except Exception as e:
        st.error(f"Error al leer el archivo CSV remoto: {str(e)[:200]}...")
        return None

def actualizar_contador_convocatorias(df):
    """Actualiza el contador de convocatorias en el CSV."""
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
    """Envía la convocatoria PDF a todos los contactos activos."""
    try:
        # Leer y actualizar el archivo CSV
        df = leer_csv_remoto()
        if df is None or df.empty:
            st.error("No se pudo cargar el archivo CSV o está vacío")
            return
        
        # Actualizar contador primero
        df = actualizar_contador_convocatorias(df)
        
        # Guardar cambios localmente
        with open(LOCAL_FILE_CSV, 'w', encoding='utf-8') as f:
            df.to_csv(f, index=False)
        
        # Subir cambios al servidor remoto
        if enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV):
            st.success("CSV actualizado en servidor remoto")
        else:
            st.warning("No se pudo actualizar el CSV remoto, continuando con envío...")

        # Verificar columnas
        if len(df.columns) < 3:
            st.error("Error: El archivo CSV debe tener al menos 3 columnas")
            return

        # Intentar identificar columnas automáticamente
        columna_correo = None
        columna_estado = None
        
        # Buscar columnas que puedan contener correos
        posibles_columnas_correo = ['correo', 'email', 'mail', 'e-mail']
        for col in df.columns:
            col_lower = col.lower()
            if any(palabra in col_lower for palabra in posibles_columnas_correo):
                columna_correo = col
                break
        
        # Si no se encuentra, usar la tercera columna (índice 2)
        if columna_correo is None and len(df.columns) >= 3:
            columna_correo = df.columns[2]
        
        # Buscar columna de estado
        posibles_columnas_estado = ['estado', 'status', 'activo', 'situacion']
        for col in df.columns:
            col_lower = col.lower()
            if any(palabra in col_lower for palabra in posibles_columnas_estado):
                columna_estado = col
                break
        
        # Si no se encuentra, usar la última columna
        if columna_estado is None:
            columna_estado = df.columns[-1]
        
        st.info(f"Columna de correo detectada: {columna_correo}")
        st.info(f"Columna de estado detectada: {columna_estado}")
        
        # Obtener correos activos
        try:
            df[columna_estado] = df[columna_estado].astype(str).str.strip().str.lower()
            correos_activos = df[df[columna_estado] == 'activo'][columna_correo].tolist()
        except:
            st.warning("No se pudo filtrar por estado 'activo'. Enviando a todos los correos...")
            correos_activos = df[columna_correo].dropna().tolist()
        
        # Filtrar solo correos válidos
        correos_activos = [str(c).strip() for c in correos_activos if pd.notna(c) and '@' in str(c)]
        
        if not correos_activos:
            st.warning("No hay correos válidos en el registro.")
            return

        if not Path(LOCAL_FILE_PDF).exists():
            st.error("Error: El archivo PDF local no existe. Por favor súbelo primero.")
            return

        # Mostrar resumen
        st.info(f"Total de correos a enviar: {len(correos_activos)}")
        
        # Confirmación del usuario
        if not st.checkbox("Confirmar envío de convocatorias"):
            st.warning("Envío cancelado por el usuario")
            return

        # Enviar convocatorias con delays y por bloques
        enviados = 0
        fallados = 0
        total_correos = len(correos_activos)
        
        # Crear barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        resultados_text = st.empty()
        
        for i, correo in enumerate(correos_activos):
            try:
                success = send_email_with_attachment(
                    email_recipient=correo.strip(),
                    subject="Nueva Convocatoria INCICh",
                    body="Adjunto encontrarás la nueva convocatoria del INCICh. Revisa los detalles en el archivo PDF.",
                    attachment_path=LOCAL_FILE_PDF
                )
                
                if success:
                    enviados += 1
                    status_text.text(f"✅ Enviado a: {correo.strip()} ({i+1}/{total_correos})")
                else:
                    fallados += 1
                    status_text.text(f"❌ Falló: {correo.strip()} ({i+1}/{total_correos})")
                
                # Actualizar barra de progreso
                progress_bar.progress((i + 1) / total_correos)
                
                # Delay entre emails
                time.sleep(DELAY_ENTRE_EMAILS)
                
                # Delay adicional después de cada bloque
                if (i + 1) % EMAILS_POR_BLOQUE == 0 and (i + 1) < total_correos:
                    status_text.text(f"⏸️ Pausa de {DELAY_ENTRE_BLOQUES} segundos después del bloque {(i + 1) // EMAILS_POR_BLOQUE}...")
                    time.sleep(DELAY_ENTRE_BLOQUES)
                    
            except Exception as e:
                fallados += 1
                st.warning(f"Error al enviar a {correo}: {str(e)[:100]}")
        
        # Mostrar resumen final
        status_text.text(f"🎉 Proceso completado!")
        resultados_text.success(f"""
        **Resumen del envío:**
        - Total de correos procesados: {total_correos}
        - ✅ Envíos exitosos: {enviados}
        - ❌ Envíos fallidos: {fallados}
        - 📊 Porcentaje de éxito: {enviados/total_correos*100:.1f}%
        """)
        
        # Enviar notificación al correo de administración
        try:
            send_email_with_attachment(
                email_recipient=NOTIFICATION_EMAIL,
                subject=f"Reporte de envío de convocatorias - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
                body=f"""
                Reporte de envío de convocatorias completado:
                
                - Total de correos procesados: {total_correos}
                - Envíos exitosos: {enviados}
                - Envíos fallidos: {fallados}
                - Porcentaje de éxito: {enviados/total_correos*100:.1f}%
                - Fecha y hora: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                """,
                attachment_path=LOCAL_FILE_PDF if Path(LOCAL_FILE_PDF).exists() else None
            )
            st.info("Reporte enviado al correo de notificación")
        except Exception as e:
            st.warning(f"No se pudo enviar el reporte: {e}")
        
    except Exception as e:
        st.error(f"Error al enviar la convocatoria: {str(e)[:200]}...")

# Verificar la contraseña al inicio
if not check_password():
    st.stop()

# Interfaz de usuario (solo se muestra si la contraseña es correcta)
st.image("escudo_COLOR.jpg", width=150)
st.title("Gestión de Convocatorias INCICh")

# Mostrar configuración de envío en sidebar
st.sidebar.header("⚙️ Configuración de Envío")
st.sidebar.info(f"""
**Configuración actual:**
- ⏱️ Delay entre emails: {DELAY_ENTRE_EMAILS} segundos
- 📦 Emails por bloque: {EMAILS_POR_BLOQUE}
- ⏸️ Delay entre bloques: {DELAY_ENTRE_BLOQUES} segundos
""")

# Configuración de codificación CSV
st.sidebar.header("📄 Configuración de CSV")
st.session_state.csv_encoding = st.sidebar.selectbox(
    "Codificación del archivo CSV:",
    ["latin-1", "utf-8", "iso-8859-1", "cp1252", "utf-8-sig", "auto"],
    index=0,
    help="Selecciona la codificación del archivo CSV. 'auto' intentará detectarla automáticamente."
)

# Información del sistema
st.sidebar.header("ℹ️ Información del Sistema")
st.sidebar.info(f"""
**Archivos remotos:**
- CSV: {REMOTE_FILE_CSV}
- PDF: {REMOTE_FILE_PDF}

**Servidor:**
- Host: {REMOTE_HOST}
- Usuario: {REMOTE_USER}
- Directorio: {REMOTE_DIR}
""")

# Sección para subir archivo CSV
st.header(f"📤 Subir {LOCAL_FILE_CSV}")
uploaded_csv = st.file_uploader("Selecciona el archivo CSV para subir", type=["csv"], key="csv_uploader")
if uploaded_csv is not None:
    try:
        with open(LOCAL_FILE_CSV, "wb") as f:
            f.write(uploaded_csv.getbuffer())
        
        # Leer y mostrar vista previa
        try:
            df_preview = pd.read_csv(LOCAL_FILE_CSV, encoding=st.session_state.csv_encoding)
            st.success(f"CSV cargado: {len(df_preview)} registros, {len(df_preview.columns)} columnas")
            
            # Mostrar vista previa
            with st.expander("📊 Vista previa del CSV (primeras 5 filas)"):
                st.dataframe(df_preview.head())
            
            # Mostrar columnas
            st.write("**Columnas detectadas:**", list(df_preview.columns))
        except Exception as e:
            st.warning(f"Error al leer el CSV: {e}. Intentando subir de todos modos...")
        
        if enviar_archivo_remoto(LOCAL_FILE_CSV, REMOTE_FILE_CSV):
            st.success("✅ CSV subido exitosamente al servidor remoto")
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo CSV: {e}")

# Sección para descargar archivo CSV
st.header(f"📥 Descargar {LOCAL_FILE_CSV}")
col1, col2 = st.columns(2)
with col1:
    if st.button("🔍 Ver CSV Actual"):
        try:
            if recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV):
                if Path(LOCAL_FILE_CSV).exists():
                    df_local = pd.read_csv(LOCAL_FILE_CSV, encoding=st.session_state.csv_encoding)
                    st.success(f"CSV cargado: {len(df_local)} registros")
                    
                    # Mostrar vista previa
                    with st.expander("📋 Contenido del CSV"):
                        st.dataframe(df_local)
                    
                    # Estadísticas
                    st.write("**Estadísticas:**")
                    if 'Correo electronico' in df_local.columns:
                        correos_validos = df_local['Correo electronico'].dropna().apply(lambda x: '@' in str(x)).sum()
                        st.write(f"- Correos válidos: {correos_validos}/{len(df_local)}")
                    if 'Numero economico' in df_local.columns:
                        contador = df_local[df_local['Correo electronico'].str.strip().str.lower() == 'abcdf2024dfabc@gmail.com']
                        if not contador.empty:
                            valor = contador.iloc[0]['Numero economico']
                            st.write(f"- Contador de convocatorias: {valor}")
                else:
                    st.error("No se pudo descargar el archivo CSV")
        except Exception as e:
            st.error(f"Error al descargar el archivo CSV: {e}")

with col2:
    if st.button("💾 Descargar CSV"):
        try:
            if recibir_archivo_remoto(REMOTE_FILE_CSV, LOCAL_FILE_CSV):
                with open(LOCAL_FILE_CSV, "rb") as file:
                    st.download_button(
                        label="📥 Descargar Registro CSV",
                        data=file,
                        file_name=LOCAL_FILE_CSV,
                        mime="text/csv"
                    )
        except Exception as e:
            st.error(f"Error al descargar el archivo CSV: {e}")

# Sección para subir archivo PDF
st.header("📤 Subir Convocatoria PDF")
uploaded_pdf = st.file_uploader("Selecciona el archivo PDF para subir", type=["pdf"], key="pdf_uploader")
if uploaded_pdf is not None:
    try:
        with open(LOCAL_FILE_PDF, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        
        # Verificar que es un PDF válido
        with open(LOCAL_FILE_PDF, "rb") as f:
            header = f.read(4)
            if header == b'%PDF':
                st.success("✅ Archivo PDF válido detectado")
                file_size = Path(LOCAL_FILE_PDF).stat().st_size
                st.info(f"📏 Tamaño del archivo: {file_size / 1024:.1f} KB")
            else:
                st.warning("⚠️ El archivo no parece ser un PDF válido")
        
        if enviar_archivo_remoto(LOCAL_FILE_PDF, REMOTE_FILE_PDF):
            st.success("✅ PDF subido exitosamente al servidor remoto")
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo PDF: {e}")

# Sección para borrar archivo PDF
st.header("🗑️ Borrar Convocatoria PDF")
if st.button("Eliminar PDF del servidor"):
    if st.checkbox("Confirmar eliminación del PDF"):
        try:
            if borrar_archivo_remoto(REMOTE_FILE_PDF):
                st.success("✅ PDF eliminado exitosamente del servidor remoto")
                
                # También eliminar localmente si existe
                if Path(LOCAL_FILE_PDF).exists():
                    Path(LOCAL_FILE_PDF).unlink()
                    st.info("📄 Archivo PDF local también eliminado")
        except Exception as e:
            st.error(f"❌ Error al borrar el archivo PDF: {e}")

# Sección para enviar convocatorias
st.header("🚀 Enviar Convocatoria a Todos los Activos")

# Pre-checks antes de enviar
st.subheader("📋 Verificaciones previas")

check_pdf = Path(LOCAL_FILE_PDF).exists()
check_csv = Path(LOCAL_FILE_CSV).exists()

col1, col2 = st.columns(2)
with col1:
    if check_pdf:
        st.success("✅ Archivo PDF disponible")
        pdf_size = Path(LOCAL_FILE_PDF).stat().st_size / 1024
        st.info(f"Tamaño: {pdf_size:.1f} KB")
    else:
        st.error("❌ No hay archivo PDF. Sube uno primero.")

with col2:
    if check_csv:
        st.success("✅ Archivo CSV disponible")
    else:
        st.warning("⚠️ No hay archivo CSV local. Se descargará del servidor.")

# Botón de envío con confirmación
if check_pdf:
    if st.button("📨 Iniciar Envío Masivo", type="primary"):
        with st.spinner("Iniciando proceso de envío..."):
            enviar_convocatoria_a_activos()
else:
    st.warning("⚠️ No se puede iniciar el envío sin archivo PDF")

# Pie de página
st.markdown("---")
st.caption(f"© {pd.Timestamp.now().year} - Sistema de Gestión de Convocatorias INCICh")
st.caption(f"Última actualización: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
