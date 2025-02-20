import streamlit as st
import pandas as pd
import paramiko

# Verifica si las claves existen en st.secrets
if "smtp_server" not in st.secrets:
    st.error("La clave 'smtp_server' no está en st.secrets. Verifica tu archivo secrets.toml.")
else:
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
    remote_file_cor = st.secrets["remote_file_cor"]  # Definir remote_file_cor
    local_file_cor = st.secrets["local_file_cor"]    # Definir local_file_cor
    remote_file_csv = st.secrets["remote_file_csv"]  # Definir remote_file_csv
    local_file_csv = st.secrets["local_file_csv"]    # Definir local_file_csv

# Función para descargar archivo remoto
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
        st.error(f"Error al sincronizar {remote_file} con el servidor remoto.")
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
recibir_archivo_remoto(remote_file_cor, local_file_cor)  # Descargar registro_correccion.csv
recibir_archivo_remoto(remote_file_csv, local_file_csv)  # Descargar registro_convocatorias.csv

# Contar los registros "Terminados" en ambos archivos
total_terminados_cor = contar_terminados(local_file_cor)
total_terminados_conv = contar_terminados(local_file_csv)

# Mostrar los resultados
if total_terminados_cor is not None:
    st.write(f"Total de registros con estado 'Terminado' en {local_file_cor}: {total_terminados_cor}")

if total_terminados_conv is not None:
    st.write(f"Total de registros con estado 'Terminado' en {local_file_csv}: {total_terminados_conv}")
