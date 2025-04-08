import streamlit as st
import pandas as pd
import paramiko
import toml
from datetime import datetime, timedelta
import subprocess

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
        df["Estado"] = df["Estado"].replace({"Activo": "En proceso"})
        
        if es_correccion:
            # Seleccionar columnas relevantes para correcciones
            columnas = [
                "Fecha", 
                "Nombre", 
                "Email", 
                "Número económico", 
                "Nombre del artículo", 
                "Servicios solicitados", 
                "Estado"
            ]
            df = df[columnas]
        else:
            # Para archivos CSV normales (suscriptores)
            columnas = ["Fecha", "Nombre completo", "Correo electronico", "Numero economico", "Estado"]
            df = df[columnas]
        
        if filtrar_fechas:
            df = filtrar_ultimos_seis_meses(df)
        
        return df
    except Exception as e:
        st.error(f"Error al leer {archivo}: {e}")
        return None

# Función para contar el total de registros usando wc -l
def contar_registros_con_wc(archivo):
    try:
        resultado = subprocess.run(["wc", "-l", archivo], capture_output=True, text=True)
        num_lineas = int(resultado.stdout.split()[0])
        return num_lineas - 1  # Restamos 1 por el encabezado
    except Exception as e:
        st.error(f"Error al contar registros con wc -l: {e}")
        return 0

# Función para obtener el número económico específico
def obtener_numero_convocatorias():
    try:
        df = pd.read_csv(local_file_csv, dtype=str)
        registro = df[
            (df["Correo electronico"] == "abcdf2024dfabc@gmail.com") & 
            (df["Fecha"] == "2025-04-05")
        ]
        if not registro.empty:
            return registro.iloc[0]["Numero economico"]
        return "0"
    except Exception as e:
        st.error(f"Error al leer número de convocatorias: {e}")
        return "0"

# Interfaz de Streamlit
st.image("escudo_COLOR.jpg", width=150)
st.title("Monitoreo de la productividad de OASIS")
fecha_actual = datetime.now().strftime("%Y-%m-%d")
st.write(f"Fecha actual: {fecha_actual}")

# Descargar archivos remotos
recibir_archivo_remoto(remote_file_cor, local_file_cor)
recibir_archivo_remoto(remote_file_csv, local_file_csv)

# Sección de Revisiones de Estilo
st.warning("Sistema: Revisión de Estilo")
df_cor = extraer_datos(local_file_cor, es_correccion=True)
if df_cor is not None:
    totales_6meses = df_cor["Estado"].value_counts().to_dict()
    df_historico = extraer_datos(local_file_cor, es_correccion=True, filtrar_fechas=False)
    totales_historico = df_historico["Estado"].value_counts().to_dict()
    total_registros_cor = contar_registros_con_wc(local_file_cor)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Últimos 6 meses")
        for estado, cantidad in totales_6meses.items():
            st.metric(label=f"Estado: {estado}", value=cantidad)
        st.metric(label="Últimos 6 meses", value=sum(totales_6meses.values()))
    
    with col2:
        st.subheader("Histórico")
        for estado, cantidad in totales_historico.items():
            st.metric(label=f"Estado: {estado}", value=cantidad)
        st.metric(label="Total", value=total_registros_cor)

# Sección de Suscriptores a Convocatorias (modificada)
st.warning("Sistema: Convocatorias")
df_con = extraer_datos(local_file_csv)
if df_con is not None:
    numero_convocatorias = obtener_numero_convocatorias()
    
    # Mostrar solo una columna (eliminada la columna de Situación)
    st.subheader("Inscritos")
    st.metric(
        label="Últimos 6 meses", 
        value=sum(df_con["Estado"].value_counts().values)
    )
    total_registros_con = contar_registros_con_wc(local_file_csv)
    st.metric(
        label="Histórico", 
        value=total_registros_con
    )
    st.metric(
        label="Convocatorias enviadas:", 
        value=numero_convocatorias
    )

