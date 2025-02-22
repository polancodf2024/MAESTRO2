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
from datetime import datetime, timedelta
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
remote_file_csv = st.secrets["remote_file_csv"]  # Definir remote_file_csv
local_file_csv = st.secrets["local_file_csv"]    # Definir local_file_csv

# Función para descargar archivo remoto correcciones
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

# Función para descargar archivo remoto convocatorias
def recibir_archivo_remoto_con():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{remote_file_csv}", local_file_csv)
        sftp.close()
        ssh.close()
        print("Archivo sincronizado correctamente.")
    except Exception as e:
        st.error("Error al sincronizar con el servidor remoto.")
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

# Función para contar registros con estado "Activo"
def contar_activos(archivo):
    try:
        # Leer el archivo CSV, omitiendo filas con problemas
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False, quotechar='"', on_bad_lines='skip')
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # Eliminar espacios en blanco
        if "Estado" in df.columns:
            df["Estado"] = df["Estado"].str.lower()
            activos = df[df["Estado"] == "activo"].shape[0]
            return activos
        else:
            st.error(f"El archivo {archivo} no contiene una columna llamada 'Estado'.")
            return None
    except Exception as e:
        st.error(f"Error al leer el archivo {archivo}: {e}")
        return None

# Función para filtrar registros de los últimos seis meses
def filtrar_ultimos_seis_meses(archivo):
    try:
        # Leer el archivo CSV, omitiendo filas con problemas
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False, quotechar='"', on_bad_lines='skip')
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # Eliminar espacios en blanco

        # Verificar si la columna "Fecha y Hora" existe
        if "Fecha y Hora" not in df.columns:
            st.error(f"El archivo {archivo} no contiene una columna llamada 'Fecha y Hora'.")
            return None

        # Convertir la columna "Fecha y Hora" a datetime
        df["Fecha y Hora"] = pd.to_datetime(df["Fecha y Hora"], errors='coerce')

        # Filtrar registros con fechas válidas
        df = df.dropna(subset=["Fecha y Hora"])

        # Obtener la fecha actual y calcular la fecha de hace seis meses
        fecha_actual = datetime.now()
        fecha_seis_meses_atras = fecha_actual - timedelta(days=180)

        # Filtrar registros de los últimos seis meses
        df_filtrado = df[df["Fecha y Hora"] >= fecha_seis_meses_atras]

        return df_filtrado

    except Exception as e:
        st.error(f"Error al leer el archivo {archivo}: {e}")
        return None

# Interfaz de Streamlit
st.image("escudo_COLOR.jpg", width=150)  # Mostrar el logo
st.title("Productividad OASIS")  # Cambiar el título

# Mostrar la fecha actual
fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.write(f"Fecha actual: {fecha_actual}")

# Descargar archivos remotos
recibir_archivo_remoto_cor()  # Descargar registro_correccion.csv
recibir_archivo_remoto_con()  # Descargar registro_convocatorias.csv

# Filtrar registros de los últimos seis meses
df_cor_filtrado = filtrar_ultimos_seis_meses(local_file_cor)
df_con_filtrado = filtrar_ultimos_seis_meses(local_file_csv)

# Contar los registros "Terminados" y "Activos" en los últimos seis meses
if df_cor_filtrado is not None:
    total_terminados_cor = df_cor_filtrado[df_cor_filtrado["Estado"].str.lower() == "terminado"].shape[0]
    total_activos_cor = df_cor_filtrado[df_cor_filtrado["Estado"].str.lower() == "activo"].shape[0]
else:
    total_terminados_cor = 0
    total_activos_cor = 0

if df_con_filtrado is not None:
    total_terminados_con = df_con_filtrado[df_con_filtrado["Estado"].str.lower() == "terminado"].shape[0]
    total_activos_con = df_con_filtrado[df_con_filtrado["Estado"].str.lower() == "activo"].shape[0]
else:
    total_terminados_con = 0
    total_activos_con = 0

# Mostrar los resultados de los últimos seis meses
st.warning("Archivo Correcciones de Estilo (Últimos 6 meses)")  # Cambiar el título
st.write(f"Total registros: activos = {total_activos_cor}, terminados = {total_terminados_cor}")

st.warning("Archivo Convocatorias Enviadas (Últimos 6 meses)")  # Cambiar el título
st.write(f"Total registros: activos = {total_activos_con}, terminados = {total_terminados_con}")

# Calcular el gran total de producción sin filtrar por fecha
total_terminados_cor_general = contar_terminados(local_file_cor)
total_terminados_con_general = contar_terminados(local_file_csv)
total_activos_cor_general = contar_activos(local_file_cor)
total_activos_con_general = contar_activos(local_file_csv)

# Mostrar el gran total de producción
st.warning("Gran Total de Producción (Sin filtrar por fecha)")
st.write(f"Total registros en correcciones: activos = {total_activos_cor_general}, terminados = {total_terminados_cor_general}")
st.write(f"Total registros en convocatorias: activos = {total_activos_con_general}, terminados = {total_terminados_con_general}")
