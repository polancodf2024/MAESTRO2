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
remote_file_cor = st.secrets["remote_file_cor"]
local_file_cor = st.secrets["local_file_cor"]



# Función para descargar archivo remoto
def recibir_archivo_remoto_cor():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{remote_file_cor}", local_file_cor)
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
        sftp.put(local_file_cor, f"{remote_dir}/{remote_file_cor}")
        sftp.close()
        ssh.close()
        print("Archivo subido al servidor remoto.")
    except Exception as e:
        st.error("Error al subir el archivo al servidor remoto.")
        st.error(str(e))
 
# Función para contar registros con estado "Terminado"
def contar_terminados(archivo):
    try:
        # Leer el archivo CSV, omitiendo filas con problemas
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False, quotechar='"', on_bad_lines='skip')
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # Eliminar espacios en blanco
        if "Estado" in df.columns:
            df["Estado"] = df["Estado"].str.lower()
            terminados = df[df["Estado"] == "terminado"].shape[0]
            return terminados
        else:
            st.error(f"El archivo {archivo} no contiene una columna llamada 'Estado'.")
            return None
    except Exception as e:
        st.error(f"Error al leer el archivo {archivo}: {e}")
        return None

# Interfaz de Streamlit
st.image("escudo_COLOR.jpg", width=150)  # Mostrar el logo
st.title("Productividad OASIS")  # Cambiar el título

# Descargar archivos remotos
recibir_archivo_remoto_cor()  # Descargar registro_correccion.csv


# Contar los registros "Terminados" en ambos archivos
total_terminados_cor = contar_terminados(local_file_cor)

# Mostrar los resultados
if total_terminados_cor is not None:
    st.write(f"Total de registros con estado 'Terminado' en {local_file_cor}: {total_terminados_cor}")

