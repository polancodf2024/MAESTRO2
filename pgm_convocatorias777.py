import streamlit as st
import csv
import os
import toml
import paramiko
from datetime import datetime
import pytz
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración inicial
config = toml.load(".streamlit/config.toml")

# Configuración del servidor y correo
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

CAMPOS = ["Fecha", "Nombre completo", "Correo electronico", "Numero economico", "Estado"]

def conectar_servidor_remoto():
    """Establece conexión con el servidor remoto"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, 
                   username=REMOTE_USER, password=REMOTE_PASSWORD)
        return ssh
    except Exception as e:
        st.error(f"Error al conectar al servidor remoto: {e}")
        return None

def descargar_archivo_remoto():
    """Descarga el archivo desde el servidor remoto"""
    ssh = conectar_servidor_remoto()
    if ssh:
        try:
            sftp = ssh.open_sftp()
            sftp.get(f"{REMOTE_DIR}/{REMOTE_FILE}", LOCAL_FILE)
            sftp.close()
            ssh.close()
            return True
        except Exception as e:
            st.error(f"Error al descargar archivo: {e}")
            return False
    return False

def subir_archivo_remoto():
    """Sube el archivo actualizado al servidor remoto"""
    ssh = conectar_servidor_remoto()
    if ssh:
        try:
            sftp = ssh.open_sftp()
            sftp.put(LOCAL_FILE, f"{REMOTE_DIR}/{REMOTE_FILE}")
            sftp.close()
            ssh.close()
            return True
        except Exception as e:
            st.error(f"Error al subir archivo: {e}")
            return False
    return False

def inicializar_archivo():
    """Inicializa el archivo local si no existe"""
    if not os.path.exists(LOCAL_FILE):
        with open(LOCAL_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CAMPOS)
            writer.writeheader()

def cargar_registros():
    """Carga registros desde el archivo local"""
    inicializar_archivo()
    registros = []
    try:
        with open(LOCAL_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                registro_normalizado = {
                    "Fecha": row.get("Fecha", "").strip(),
                    "Nombre completo": row.get("Nombre completo", "").strip(),
                    "Correo electronico": row.get("Correo electronico", "").strip().lower(),
                    "Numero economico": row.get("Numero economico", "").strip(),
                    "Estado": row.get("Estado", "").strip()
                }
                registros.append(registro_normalizado)
    except Exception as e:
        st.error(f"Error al leer archivo local: {e}")
    return registros

def guardar_registros(registros):
    """Guarda registros en el archivo local"""
    try:
        with open(LOCAL_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CAMPOS)
            writer.writeheader()
            writer.writerows(registros)
    except Exception as e:
        st.error(f"Error al guardar archivo local: {e}")

def sincronizar_registros():
    """Sincroniza los registros con el servidor remoto"""
    if not descargar_archivo_remoto():
        st.warning("No se pudo descargar archivo remoto, usando versión local")
    registros = cargar_registros()
    return registros

def buscar_correo(correo):
    """Busca un correo en los registros"""
    registros = sincronizar_registros()
    correo_buscado = correo.strip().lower()
    for registro in registros:
        if registro["Correo electronico"] == correo_buscado:
            return registro
    return None

def registrar_usuario(correo, nombre, numero_economico):
    """Registra un nuevo usuario"""
    registros = sincronizar_registros()
    
    # Verificar si el correo ya existe (incluyendo mayúsculas/minúsculas)
    for reg in registros:
        if reg["Correo electronico"].lower() == correo.strip().lower():
            st.error("Este correo electrónico ya está registrado")
            return False
    
    nuevo_registro = {
        "Fecha": datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d"),
        "Nombre completo": nombre.strip(),
        "Correo electronico": correo.strip().lower(),
        "Numero economico": numero_economico.strip(),
        "Estado": "Activo"
    }
    
    registros.append(nuevo_registro)
    guardar_registros(registros)
    if subir_archivo_remoto():
        enviar_email_confirmacion(correo, nombre, "Confirmación de inscripción")
        return True
    return False

def cambiar_estado_usuario(correo, nuevo_estado):
    """Cambia el estado del usuario (Activo/Inactivo)"""
    registros = sincronizar_registros()
    correo_buscado = correo.strip().lower()
    modificado = False
    
    for registro in registros:
        if registro["Correo electronico"] == correo_buscado:
            registro["Estado"] = nuevo_estado
            modificado = True
            break
    
    if modificado:
        guardar_registros(registros)
        if subir_archivo_remoto():
            accion = "reactivación" if nuevo_estado == "Activo" else "baja"
            enviar_email_confirmacion(correo, registro.get("Nombre completo", ""), f"Confirmación de {accion}")
            return True
    return False

def actualizar_usuario(correo_original, nuevo_correo, nuevo_nombre, nuevo_numero):
    """Actualiza todos los datos del usuario y reactiva la suscripción"""
    registros = sincronizar_registros()
    correo_original = correo_original.strip().lower()
    nuevo_correo = nuevo_correo.strip().lower()
    modificado = False
    
    # Verificar si el nuevo correo ya existe (para otro usuario)
    if nuevo_correo != correo_original:
        for reg in registros:
            if reg["Correo electronico"] == nuevo_correo and reg["Correo electronico"] != correo_original:
                st.error("El nuevo correo electrónico ya está registrado para otro usuario")
                return False
    
    for registro in registros:
        if registro["Correo electronico"] == correo_original:
            # Actualizar todos los campos
            registro["Nombre completo"] = nuevo_nombre.strip()
            registro["Correo electronico"] = nuevo_correo
            registro["Numero economico"] = nuevo_numero.strip()
            registro["Estado"] = "Activo"
            registro["Fecha"] = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
            modificado = True
            break
    
    if modificado:
        guardar_registros(registros)
        if subir_archivo_remoto():
            enviar_email_confirmacion(nuevo_correo, nuevo_nombre, "Actualización de datos y reactivación")
            return True
    return False

def enviar_email_confirmacion(correo, nombre, asunto):
    """Envía email de confirmación"""
    try:
        mensaje = MIMEMultipart()
        mensaje['From'] = EMAIL_USER
        mensaje['To'] = correo
        mensaje['Subject'] = f"Convocatorias - {asunto}"
        
        cuerpo = f"Hola {nombre},\n\n" if nombre else "Hola,\n\n"
        cuerpo += "Tus datos de suscripción han sido actualizados:\n\n"
        cuerpo += f"**Acción realizada:** {asunto}\n"
        cuerpo += f"**Fecha:** {datetime.now(pytz.timezone('America/Mexico_City')).strftime('%Y-%m-%d %H:%M')}\n\n"
        cuerpo += "Gracias por utilizar nuestro servicio.\n\nSaludos cordiales."
        
        mensaje.attach(MIMEText(cuerpo, 'plain'))
        
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, correo, mensaje.as_string())
    except Exception as e:
        st.error(f"Error al enviar email: {e}")

# Interfaz de Usuario
st.title("Sistema de convocatorias OASIS")
st.image("escudo_COLOR.jpg", width=200)

correo = st.text_input("Ingrese su correo electrónico y presione ENTER:")

if correo:
    registro = buscar_correo(correo)
    
    if registro:
        st.subheader("Datos del Registro")
        
        if registro["Estado"] == "Inactivo":
            with st.form("form_reactivar"):
                st.write("**Actualice sus datos y reactive su suscripción:**")
                
                nuevo_correo = st.text_input("Nuevo correo electrónico:", value=registro["Correo electronico"])
                nuevo_nombre = st.text_input("Nombre completo:", value=registro["Nombre completo"])
                nuevo_numero = st.text_input("Número económico:", value=registro["Numero economico"])
                
                if st.form_submit_button("Guardar cambios y reactivar"):
                    if not all([nuevo_correo, nuevo_nombre, nuevo_numero]):
                        st.error("Complete todos los campos")
                    elif actualizar_usuario(correo, nuevo_correo, nuevo_nombre, nuevo_numero):
                        st.success("¡Datos actualizados y suscripción reactivada!")
                    else:
                        st.error("Error al actualizar los datos")
        
        else:  # Si está activo
            st.write(f"**Nombre:** {registro['Nombre completo']}")
            st.write(f"**Correo electrónico:** {registro['Correo electronico']}")
            st.write(f"**Número económico:** {registro['Numero economico']}")
            st.write(f"**Estado:** {registro['Estado']}")
            
            if st.button("Darse de baja"):
                if cambiar_estado_usuario(correo, "Inactivo"):
                    st.success("Estado actualizado: Dado de baja")
                else:
                    st.error("Error al actualizar el estado")
    
    else:  # Nuevo registro
        st.subheader("Nuevo Registro")
        nombre = st.text_input("Nombre completo:")
        numero_economico = st.text_input("Número económico:")
        
        if st.button("Registrarse"):
            if not all([correo, nombre, numero_economico]):
                st.error("Complete todos los campos")
            elif registrar_usuario(correo, nombre, numero_economico):
                st.success("¡Registro exitoso!")
            else:
                st.error("Error al registrar")
