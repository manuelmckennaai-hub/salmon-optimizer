import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

st.set_page_config(page_title="SalmonFeed AI", layout="wide")
st.title("🐟 SalmonFeed AI - Optimizador B2B")
st.markdown("Integrando la ecuación de Consumo de Oxígeno (MO2) de Hvas et al. y Evasión Espacial.")

# --- MÓDULOS DEL MOTOR ---
class SparseEnvironmentInterpolator:
    @staticmethod
    def generar_perfil_completo(t_sup, do_sup, t_fon, do_fon):
        profundidades = [1, 15]
        temps = [t_sup, t_fon]
        dos = [do_sup, do_fon]
        z_array = np.linspace(1, 15, 50)
        temp_array = PchipInterpolator(profundidades, temps)(z_array)
        do_array = np.clip(PchipInterpolator(profundidades, dos)(z_array), 0, 100)
        return z_array, temp_array, do_array

class FisiologiaHvas:
    @staticmethod
    def calcular_mo2_basal(peso_kg, temp_c, vel_natacion_bl_s):
        """Ecuación Fundamental de Hvas (Nature)"""
        # MO2 = 79.7 * W^(-0.14) * 1.04^T * 1.63^U
        mo2 = 79.7 * (peso_kg ** -0.14) * (1.04 ** temp_c) * (1.63 ** vel_natacion_bl_s)
        return mo2

class SDA_Nutricional:
    @staticmethod
    def multiplicador_macronutrientes(pct_prot, pct_lip, pct_carb):
        costo_dieta = (pct_prot * 0.25) + (pct_lip * 0.04) + (pct_carb * 0.12)
        costo_estandar = (45 * 0.25) + (28 * 0.04) + (12 * 0.12)
        return 1.0 + (0.4 * (costo_dieta / costo_estandar))

# --- INTERFAZ SIDEBAR ---
st.sidebar.header("1. Biometría del Pez")
peso_pez = st.sidebar.number_input("Peso Promedio (kg)", value=2.5, step=0.5)
vel_natacion = st.sidebar.slider("Natación (BL/s)", 0.1, 2.0, 0.5)
racion = st.sidebar.number_input("Ración a Disparar (kg)", value=1000)

st.sidebar.header("2. Dieta (Etiqueta Proximal)")
pct_prot = st.sidebar.slider("% Proteína Cruda", 30.0, 60.0, 45.0)
pct_lip = st.sidebar.slider("% Lípidos", 15.0, 40.0, 28.0)
pct_carb = st.sidebar.slider("% Carbohidratos", 5.0, 25.0, 12.0)

st.sidebar.header("3. Sensores Escasos (Sparse Data)")
t_sup = st.sidebar.number_input("Temp Superficie (°C)", value=14.5)
do_sup = st.sidebar.number_input("DO Superficie (%)", value=85.0)
t_fon = st.sidebar.number_input("Temp Fondo (15m) (°C)", value=10.0)
do_fon = st.sidebar.number_input("DO Fondo (15m) (%)", value=60.0)

# --- EJECUCIÓN ---
z_array, temp_array, do_array = SparseEnvironmentInterpolator.generar_perfil_completo(t_sup, do_sup, t_fon, do_fon)
idx_opt = np.argmin(np.abs(temp_array - 13.5))
prof_opt = z_array[idx_opt]
temp_pez = temp_array[idx_opt]
do_pez = do_array[idx_opt]

# Cálculos Metabólicos (Hvas + Goodrich)
mo2_basal = FisiologiaHvas.calcular_mo2_basal(peso_pez, temp_pez, vel_natacion)
sda_mult = SDA_Nutricional.multiplicador_macronutrientes(pct_prot, pct_lip, pct_carb)
mo2_postprandial = mo2_basal * sda_mult

# Conversión a Requerimiento de DO en Jaula
do_req_basal = max(30.0, min((3.75 * temp_pez) + 10.0, 100.0))
do_req_total = do_req_basal * sda_mult

if do_pez >= do_req_total:
    estado, color, r_final = "✅ ALIMENTACIÓN AUTORIZADA", "green", racion
else:
    estado, color, r_final = "🛑 BLOQUEO METABÓLICO (SDA)", "red", racion * (do_pez / do_req_total)

# --- DASHBOARD ---
col1, col2, col3 = st.columns(3)
col1.metric("Hábitat Interpolado", f"{prof_opt:.1f} m", f"{temp_pez:.1f} °C")
col2.metric("MO2 Post-Prandial (Hvas)", f"{mo2_postprandial:.0f} mg O2/kg/h", f"Basal: {mo2_basal:.0f}")
col3.metric("Requisito vs Disponible", f"{do_req_total:.1f}% DO Req.", f"{do_pez:.1f}% DO Real", delta_color="inverse")

st.markdown("---")
st.subheader(f"Veredicto: {estado}")
st.info(f"**Análisis Financiero:** Se bloqueó el disparo de {racion - r_final:.0f} kg de alimento previniendo hipoxia letal. Retorno de Inversión (ROI) instantáneo: ${(racion - r_final) * 1.8:.0f} USD.")
