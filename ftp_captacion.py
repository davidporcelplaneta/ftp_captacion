import os
from ftplib import FTP
import pandas as pd
from datetime import datetime
import streamlit as st
import zipfile
import shutil

# ======================
# CONFIGURACIÓN
# ======================
FTP_HOST = "thirsty-joliot.213-165-69-91.plesk.page"
FTP_USER = "leads_bequers_azerca"
FTP_PASS = "ls0L0i!51G73O$as"

FTP_CONFIG = {
    "/azerca": {
        "prefix": "qadk920_leads_",
        "output_file": "azerca.xlsx"
    },
    "/bequers": {
        "prefix": "qalc639_leads_",
        "output_file": "bequers.xlsx"
    },
    "/azerca_guias": {
        "prefix": "qaij634_leads_",
        "output_file": "azerca_guias.xlsx"
    }
}

LOCAL_DIR = "./leads"
TXT_DIR = os.path.join(LOCAL_DIR, "txt_files")
XLSX_DIR = os.path.join(LOCAL_DIR, "xlsx_files")
LOG_FILE = "leads.log"

os.makedirs(TXT_DIR, exist_ok=True)
os.makedirs(XLSX_DIR, exist_ok=True)

# ======================
# LOG LOCAL
# ======================
def registrar_log_local(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] {msg}\n")

# ======================
# DESCARGA DE ARCHIVOS FTP
# ======================
def download_all_files(progress_bar):
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)

    for dir_path, conf in FTP_CONFIG.items():
        try:
            ftp.cwd(dir_path)
            files = ftp.nlst()
        except Exception as e:
            registrar_log_local(f"Error accediendo a {dir_path}: {e}")
            continue

        archivos_txt = [f for f in files if f.endswith(".txt") and conf["prefix"] in f]

        if not archivos_txt:
            registrar_log_local(f"No se encontraron archivos con prefijo {conf['prefix']} en {dir_path}")
            continue

        # Barra de progreso para la descarga
        for idx, filename in enumerate(archivos_txt):
            local_path = os.path.join(TXT_DIR, filename)
            try:
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                progress_bar.progress((idx + 1) / len(archivos_txt))
            except Exception as e:
                registrar_log_local(f"Error descargando {filename}: {e}")
                continue

    ftp.quit()

# ======================
# GENERAR EXCEL UNIFICADO POR CARPETA
# ======================
def generar_excels(progress_bar):
    for dir_path, conf in FTP_CONFIG.items():
        prefix = conf["prefix"]
        output_path = os.path.join(XLSX_DIR, conf["output_file"])

        archivos_txt = [f for f in os.listdir(TXT_DIR) if f.endswith(".txt") and prefix in f]

        if not archivos_txt:
            registrar_log_local(f"No se encontraron archivos con prefijo {prefix}")
            continue

        df_total = pd.DataFrame()
        archivos_procesados = 0
        errores = 0

        for idx, archivo in enumerate(archivos_txt):
            file_path = os.path.join(TXT_DIR, archivo)
            df = None

            for encoding in ["utf-8", "cp1252", "latin-1"]:
                try:
                    df = pd.read_csv(file_path, sep=";", encoding=encoding)
                    registrar_log_local(f"{archivo} leído correctamente con {encoding}")
                    break
                except Exception as e:
                    registrar_log_local(f"Error leyendo {archivo} con {encoding}: {e}")

            if df is None:
                registrar_log_local(f"No se pudo leer el archivo {archivo}")
                errores += 1
                continue

            # Verificamos que el DataFrame no esté vacío antes de agregarlo
            if not df.empty:
                df_total = pd.concat([df_total, df], ignore_index=True)
                archivos_procesados += 1
            else:
                registrar_log_local(f"El archivo {archivo} está vacío.")
            
            progress_bar.progress((idx + 1) / len(archivos_txt))

        if not df_total.empty:
            # Guardar archivo Excel
            df_total.to_excel(output_path, index=False)
            total_filas = len(df_total)
            registrar_log_local(f"Excel generado: {output_path} ({total_filas} filas)")
        else:
            registrar_log_local(f"No se generó ningún Excel para {dir_path} debido a errores o archivos vacíos.")

    return archivos_procesados, errores

# ======================
# CREAR UN ARCHIVO ZIP QUE CONTENGA TANTO TXT COMO XLSX
# ======================
def crear_zip_completo():
    # Creamos un directorio temporal para agrupar los archivos .txt y .xlsx
    zip_name = "./leads_completo.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Agregar archivos .txt
        for root, dirs, files in os.walk(TXT_DIR):
            for file in files:
                if file.endswith(".txt"):
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), TXT_DIR))
        # Agregar archivos .xlsx
        for root, dirs, files in os.walk(XLSX_DIR):
            for file in files:
                if file.endswith(".xlsx"):
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), XLSX_DIR))
    
    return zip_name

# ======================
# STREAMLIT INTERFAZ
# ======================
def run_streamlit_app():
    st.title("Procesamiento de Archivos FTP y Generación de Excel")

    if st.button('Ejecutar todo el proceso'):
        # Barra de progreso general
        progress_bar = st.progress(0)

        try:
            # Paso 1: Descargar archivos TXT
            st.write("Iniciando descarga de archivos...")
            download_all_files(progress_bar)
            st.write("Archivos TXT descargados con éxito.")

            # Paso 2: Generar los archivos Excel
            st.write("Generando archivos Excel...")
            archivos_procesados, errores = generar_excels(progress_bar)
            st.write(f"Archivos Excel generados. Archivos procesados: {archivos_procesados}, Errores: {errores}")

            # Paso 3: Crear el archivo zip que contiene los .txt y .xlsx
            st.write("Creando archivo comprimido con TXT y XLSX...")
            zip_completo = crear_zip_completo()

            # Paso 4: Enlace de descarga del archivo zip
            st.write("Descarga disponible:")
            st.download_button("Descargar todos los archivos", zip_completo, file_name="leads_completo.zip")

        except Exception as e:
            st.error(f"Ocurrió un error durante el proceso: {e}")
            registrar_log_local(f"Error general: {e}")

# ======================
# EJECUCIÓN STREAMLIT
# ======================
if __name__ == "__main__":
    run_streamlit_app()
