import os
from ftplib import FTP
import pandas as pd
from datetime import datetime
from tqdm import tqdm  # Para la barra de progreso
import streamlit as st

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
def download_all_files():
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
        with tqdm(total=len(archivos_txt), desc=f"Descargando archivos de {dir_path}", unit="archivo") as pbar:
            for filename in archivos_txt:
                local_path = os.path.join(TXT_DIR, filename)
                try:
                    with open(local_path, 'wb') as f:
                        ftp.retrbinary(f'RETR {filename}', f.write)
                    pbar.set_postfix({"archivo": filename})  # Mostrar el nombre del archivo descargado
                    pbar.update(1)  # Avanzar en la barra de progreso
                except Exception as e:
                    registrar_log_local(f"Error descargando {filename}: {e}")
                    pbar.set_postfix({"error": filename})  # Mostrar el nombre del archivo con error
                    pbar.update(1)  # Avanzar en la barra de progreso

    ftp.quit()

# ======================
# GENERAR EXCEL UNIFICADO POR CARPETA
# ======================
def generar_excels():
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

        # Barra de progreso para el procesamiento de archivos
        with tqdm(total=len(archivos_txt), desc=f"Procesando archivos en {dir_path}", unit="archivo") as pbar:
            for archivo in archivos_txt:
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
                    pbar.set_postfix({"error": archivo})  # Mostrar el archivo con error en la barra
                    pbar.update(1)  # Avanzar en la barra
                    continue

                df_total = pd.concat([df_total, df], ignore_index=True)
                archivos_procesados += 1
                # Actualizar la barra de progreso con el número de filas procesadas
                pbar.set_postfix({"archivo": archivo, "filas procesadas": len(df_total)})
                pbar.update(1)  # Avanzar en la barra

        if not df_total.empty:
            # Guardar archivo Excel
            df_total.to_excel(output_path, index=False)
            total_filas = len(df_total)
            registrar_log_local(f"Excel generado: {output_path} ({total_filas} filas)")
            st.write(f"Excel generado: {output_path} ({total_filas} filas)")
        else:
            registrar_log_local(f"No se generó ningún Excel para {dir_path} debido a errores.")
            st.write(f"No se generó ningún Excel para {dir_path} debido a errores.")

        registrar_log_local(f"Archivos procesados correctamente: {archivos_procesados}")
        registrar_log_local(f"Errores durante el proceso: {errores}")

# ======================
# STREAMLIT INTERFAZ
# ======================
def run_streamlit_app():
    st.title("Procesamiento de Archivos FTP y Generación de Excel")
    
    if st.button('Descargar Archivos FTP'):
        st.write("Iniciando descarga de archivos...")
        download_all_files()
        st.write("Archivos descargados con éxito.")
    
    if st.button('Generar Archivos Excel'):
        st.write("Generando archivos Excel...")
        generar_excels()
        st.write("Archivos Excel generados.")

# ======================
# EJECUCIÓN STREAMLIT
# ======================
if __name__ == "__main__":
    run_streamlit_app()
