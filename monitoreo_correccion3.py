import streamlit as st
import pandas as pd
import paramiko
import toml
from datetime import datetime, timedelta

# Leer configuraciones locales desde config.toml
config = toml.load(".streamlit/config.toml")

# Configuración del servidor
smtp_server = st.secrets["smtp_server"]
remote_host = st.secrets["remote_host"]
remote_user = st.secrets["remote_user"]
remote_password = st.secrets["remote_password"]
remote_port = st.secrets["remote_port"]
remote_dir = st.secrets["remote_dir"]
remote_file_cor = st.secrets["remote_file_cor"]
local_file_cor = st.secrets["local_file_cor"]
remote_file_csv = st.secrets["remote_file_csv"]
local_file_csv = st.secrets["local_file_csv"]

# Función para descargar archivos remotos
def recibir_archivo_remoto(remote_file, local_file):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_password)
        sftp = ssh.open_sftp()
        sftp.get(f"{remote_dir}/{remote_file}", local_file)
        sftp.close()
        ssh.close()
        print(f"Archivo {remote_file} sincronizado correctamente.")
    except Exception as e:
        st.error(f"Error al sincronizar {remote_file}: {e}")

# Función para filtrar los últimos 6 meses
def filtrar_ultimos_seis_meses(df):
    try:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce').dt.date
        fecha_limite = datetime.now().date() - timedelta(days=180)
        df = df[df["Fecha"] >= fecha_limite]
        return df
    except Exception as e:
        st.error(f"Error al filtrar por fecha: {e}")
        return df

# Función para leer y extraer datos
def extraer_datos(archivo, es_correccion=False, filtrar_fechas=True):
    try:
        df = pd.read_csv(archivo, dtype=str, keep_default_na=False, on_bad_lines='skip')
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        if es_correccion:
            columnas = ["Fecha", "Nombre del Artículo", df.columns[-1]]
        else:
            columnas = ["Fecha", df.columns[-1]]
        
        df = df[columnas]
        df.columns = ["Fecha", "Nombre del Artículo", "Estado"] if es_correccion else ["Fecha", "Estado"]
        
        if filtrar_fechas:
            df = filtrar_ultimos_seis_meses(df)
        
        return df
    except Exception as e:
        st.error(f"Error al leer {archivo}: {e}")
        return None

# Función para calcular totales por estado
def calcular_totales(df):
    if df is not None:
        return df["Estado"].value_counts().to_dict()
    return {}

# Interfaz de Streamlit
st.image("escudo_COLOR.jpg", width=150)
st.title("Productividad OASIS")
fecha_actual = datetime.now().strftime("%Y-%m-%d")
st.write(f"Fecha actual: {fecha_actual}")

# Descargar archivos remotos
recibir_archivo_remoto(remote_file_cor, local_file_cor)
recibir_archivo_remoto(remote_file_csv, local_file_csv)

# Extraer y mostrar datos
st.warning("Sistema de revisión de estilo")
df_cor = extraer_datos(local_file_cor, es_correccion=True)
if df_cor is not None:
    df_cor.index = df_cor.index + 1
    st.dataframe(df_cor)
    totales_cor = calcular_totales(df_cor)
    for estado, cantidad in totales_cor.items():
        st.write(f"Revisiones con estado: {estado}: {cantidad}")
    st.write(f"Total revisiones de los últimos seis meses: {sum(totales_cor.values())}")

df_cor_total = extraer_datos(local_file_cor, es_correccion=True, filtrar_fechas=False)
if df_cor_total is not None:
    st.write(f"Total revisiones desde su fundación: {len(df_cor_total)}")

st.warning("Sistema de suscriptores a convocatorias")
df_con = extraer_datos(local_file_csv)
if df_con is not None:
    df_con.index = df_con.index + 1
    totales_con = calcular_totales(df_con)
    for estado, cantidad in totales_con.items():
        st.write(f"Suscriptores con estado: {estado}: {cantidad}")
    st.write(f"Total suscriptores de los últimos seis meses: {sum(totales_con.values())}")

df_con_total = extraer_datos(local_file_csv, filtrar_fechas=False)
if df_con_total is not None:
    st.write(f"Total suscriptores desde su fundación: {len(df_con_total)}")
