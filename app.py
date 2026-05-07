import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import pandas as pd
import json

# Configuración de alcance para acceso a APIs de Google
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def conectar_bd_gastos():
    """
    Establece conexión con la hoja de cálculo de gastos médicos.
    Soporta entornos locales mediante archivo físico y despliegues mediante variables de entorno.
    """
    if "GCP_CREDENTIALS" in st.secrets:
        creds_dict = json.loads(st.secrets["GCP_CREDENTIALS"])
        credenciales = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        ruta_credenciales = os.path.join(os.path.dirname(__file__), "credenciales.json")
        credenciales = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
        
    cliente = gspread.authorize(credenciales)
    return cliente.open("Gastos_Medicos").sheet1

# Configuración principal de la interfaz web
st.set_page_config(page_title="Control de Gastos Médicos", layout="wide")
st.title("Gestión de Reembolsos y Gastos")

tab_registro, tab_finanzas = st.tabs(["Ingresar Documento", "Estado de Reembolsos"])

with tab_registro:
    with st.form("formulario_gastos"):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("Fecha de emisión", datetime.now())
            concepto = st.text_input("Concepto (Ej: Nebivolol, Consulta)")
            monto = st.number_input("Monto Total ($)", min_value=0, step=1000)
            
        with col2:
            estado = st.selectbox("Estado del trámite", ["Pendiente", "Reembolsado"])
            comentario = st.text_area("Notas adicionales")
            # El componente UI está presente, requiere integración de backend para procesar el archivo físico
            boleta = st.file_uploader("Adjuntar Boleta/Factura", type=['png', 'jpg', 'pdf'])
            
        enviado = st.form_submit_button("Registrar Transacción")
        
        if enviado:
            try:
                hoja = conectar_bd_gastos()
                url_archivo = "Pendiente de integración API Drive" 
                
                datos = [
                    fecha.strftime("%d/%m/%Y"),
                    concepto,
                    monto,
                    estado,
                    comentario,
                    url_archivo
                ]
                hoja.append_row(datos)
                st.success("Transacción registrada correctamente en la base de datos.")
            except Exception as e:
                st.error(f"Fallo de escritura en base de datos: {e}")

with tab_finanzas:
    st.header("Panel Financiero")
    
    if st.button("Actualizar Métricas"):
        try:
            hoja = conectar_bd_gastos()
            registros = hoja.get_all_records()
            
            if registros:
                df = pd.DataFrame(registros)
                
                # Transformación de tipos de datos para permitir operaciones aritméticas
                df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
                
                # Cálculo de indicadores clave de rendimiento (KPIs)
                total_gastado = df['Monto'].sum()
                total_pendiente = df[df['Estado'] == 'Pendiente']['Monto'].sum()
                total_reembolsado = df[df['Estado'] == 'Reembolsado']['Monto'].sum()
                
                col_k1, col_k2, col_k3 = st.columns(3)
                col_k1.metric("Gasto Total Histórico", f"${total_gastado:,.0f}")
                col_k2.metric("Capital Retenido (Pendiente)", f"${total_pendiente:,.0f}", delta="Por recuperar", delta_color="inverse")
                col_k3.metric("Capital Recuperado", f"${total_reembolsado:,.0f}")
                
                st.divider()
                st.subheader("Desglose Histórico")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No existen registros procesables en la hoja de cálculo.")
        except Exception as e:
            st.error(f"Error en el motor de procesamiento de datos: {e}")