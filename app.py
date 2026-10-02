import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

st.set_page_config(page_title="SalmonFeed SaaS", layout="wide")
st.title("🐟 SalmonFeed - Optimizador Metabólico B2B")
st.markdown("Motor predictivo de evasión espacial y cálculo de SDA (Basado en modelos empíricos de Hvas et al. y Oppedal)")

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
        """Ecuación Fundamental de Hvas (Nature 2026)"""
        return 79.7 * (peso_kg ** -0.14) * (1.04 ** temp_c) * (1.63 ** vel_natacion_bl_s)

class SDA_Nutricional:
    @staticmethod
    def multiplicador_macronutrientes(pct_prot, pct_lip, pct_carb):
        costo_dieta = (pct_prot * 0.25) + (pct_lip * 0.04) + (pct_carb * 0.12)
        costo_estandar = (45 * 0.25) + (28 * 0.04) + (12 * 0.12)
        return 1.0 + (0.4 * (costo_dieta / costo_estandar))

# --- INTERFAZ SIDEBAR ---
st.sidebar.header("1. Parámetros Operativos")
peso_pez = st.sidebar.number_input("Peso Promedio (kg)", value=2.5, step=0.5)
vel_natacion = st.sidebar.slider("Vel. Natación (BL/s)", 0.1, 2.0, 0.5)
racion = st.sidebar.number_input("Ración a Disparar (kg)", value=1000, step=100)
precio_alimento = st.sidebar.number_input("Costo Alimento (USD/kg)", value=1.80, step=0.1)

st.sidebar.header("2. Dieta (Etiqueta Proximal)")
pct_prot = st.sidebar.slider("% Proteína Cruda", 30.0, 60.0, 46.5)
pct_lip = st.sidebar.slider("% Lípidos", 15.0, 40.0, 28.0)
pct_carb = st.sidebar.slider("% Carbohidratos", 5.0, 25.0, 12.0)

st.sidebar.header("3. Telemetría de Sensores")
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

do_req_basal = max(30.0, min((3.75 * temp_pez) + 10.0, 100.0))
do_req_total = do_req_basal * sda_mult

if do_pez >= do_req_total:
    estado, color, r_final = "✅ SÍNTESIS ÓPTIMA (ALIMENTAR)", "green", racion
    alerta = "El ambiente soporta la asimilación de macronutrientes. Alimentación autorizada."
else:
    factor = do_pez / do_req_total
    r_final = racion * factor
    estado, color = "🛑 RIESGO DE ASFIXIA POST-PRANDIAL", "red"
    alerta = f"Oxígeno insuficiente ({do_pez:.1f}%) para procesar el SDA de la dieta. Bloqueo preventivo activado."

kg_salvados = racion - r_final
roi_usd = kg_salvados * precio_alimento

# --- DASHBOARD VISUAL ---
col1, col2, col3 = st.columns(3)
col1.metric("Hábitat del Cardumen", f"{prof_opt:.1f} m", f"Temp: {temp_pez:.1f} °C")
col2.metric("Límite de Asfixia (SDA)", f"{do_req_total:.1f}% DO Req", f"MO2 Post-Prandial: {mo2_postprandial:.0f} mg/kg/h", delta_color="inverse")
col3.metric("Ahorro Financiero (ROI)", f"${roi_usd:,.0f} USD", f"{kg_salvados:,.0f} kg bloqueados")

st.markdown("---")
st.subheader(f"Veredicto del Motor: {estado}")
st.info(alerta)

# Gráfico de Interpolación y Decisión
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(temp_array, z_array, 'r-', linewidth=2, label='Temp Interpolada (°C)')
ax.plot(do_array, z_array, 'b-', linewidth=2, label='DO Interpolado (%)')
ax.axhline(prof_opt, color='green', linestyle='--', label=f'Hábitat Pez ({prof_opt:.1f}m)')
ax.axvline(do_req_total, color='black', linestyle=':', label=f'Límite Asfixia SDA ({do_req_total:.1f}%)')
ax.invert_yaxis()
ax.set_ylabel("Profundidad (m)")
ax.legend()
ax.grid(alpha=0.3)

st.pyplot(fig)
