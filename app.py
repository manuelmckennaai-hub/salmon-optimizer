import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="SalmonFeed AI Optimizer", layout="wide")
st.title("🐟 SalmonFeed AI - Optimizador Metabólico SaaS")
st.markdown("Algoritmo predictivo de evasión espacial y cálculo de Deuda de Oxígeno (SDA) basado en macronutrientes.")

# --- MÓDULOS MATEMÁTICOS DEL MOTOR ---
class SparseEnvironmentInterpolator:
    @staticmethod
    def generar_perfil_completo(prof_sup, temp_sup, do_sup, prof_fondo, temp_fondo, do_fondo):
        profundidades = [prof_sup, prof_fondo]
        temps = [temp_sup, temp_fondo]
        dos = [do_sup, do_fondo]
        
        interp_temp = PchipInterpolator(profundidades, temps)
        interp_do = PchipInterpolator(profundidades, dos)
        
        z_array = np.linspace(prof_sup, prof_fondo, 50)
        temp_array = interp_temp(z_array)
        do_array = interp_do(z_array)
        
        # Clip DO limits
        do_array = np.clip(do_array, 0, 100)
        return z_array, temp_array, do_array

class MacronutrientSDAModel:
    @staticmethod
    def calcular_multiplicador_sda(pct_proteina, pct_lipidos, pct_carbohidratos):
        """
        Calcula el SDA dinámico basado en la termodinámica de los macronutrientes.
        Costos metabólicos relativos: Proteína (25%), Carbohidratos (12%), Lípidos (4%).
        """
        costo_proteina = 0.25
        costo_lipidos = 0.04
        costo_carbohidratos = 0.12
        
        # Costo energético ponderado de la dieta actual
        costo_dieta = (pct_proteina * costo_proteina) + (pct_lipidos * costo_lipidos) + (pct_carbohidratos * costo_carbohidratos)
        
        # Normalizado contra una dieta estándar de la industria (45% P, 28% L, 12% C) que genera el SDA de 1.4x (Bergsson 2023)
        costo_estandar = (45 * costo_proteina) + (28 * costo_lipidos) + (12 * costo_carbohidratos)
        
        # Multiplicador SDA dinámico
        multiplicador_dinamico = 1.0 + (0.4 * (costo_dieta / costo_estandar))
        return multiplicador_dinamico

# --- INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("1. Parámetros del Centro")
biomasa_kg = st.sidebar.number_input("Biomasa de la Jaula (kg)", value=50000, step=1000)
racion_propuesta = st.sidebar.number_input("Ración a Disparar (kg)", value=1000, step=100)
precio_alimento = st.sidebar.number_input("Costo Alimento (USD/kg)", value=1.80, step=0.1)

st.sidebar.header("2. Etiqueta del Pellet (Proximal)")
pct_proteina = st.sidebar.slider("% Proteína Cruda", 30.0, 60.0, 45.0)
pct_lipidos = st.sidebar.slider("% Lípidos (Grasa)", 15.0, 40.0, 28.0)
pct_carbos = st.sidebar.slider("% Carbohidratos", 5.0, 25.0, 12.0)

st.sidebar.header("3. Telemetría de Sensores (Sparse Data)")
t_sup = st.sidebar.number_input("Temp Superficie (°C)", value=17.0)
do_sup = st.sidebar.number_input("DO Superficie (%)", value=82.0)
t_fon = st.sidebar.number_input("Temp Fondo (15m) (°C)", value=11.0)
do_fon = st.sidebar.number_input("DO Fondo (15m) (%)", value=55.0)

# --- EJECUCIÓN DEL ALGORITMO ---
# 1. Gemelo Digital
z_array, temp_array, do_array = SparseEnvironmentInterpolator.generar_perfil_completo(1, t_sup, do_sup, 15, t_fon, do_fon)

# 2. Búsqueda Espacial (T_opt = 13.5)
idx_optimo = np.argmin(np.abs(temp_array - 13.5))
prof_optima = z_array[idx_optimo]
temp_efectiva = temp_array[idx_optimo]
do_efectivo = do_array[idx_optimo]

# 3. Modelado Nutricional (SDA por Macronutrientes)
sda_multiplier = MacronutrientSDAModel.calcular_multiplicador_sda(pct_proteina, pct_lipidos, pct_carbos)
do_crit_basal = max(30.0, min((3.75 * temp_efectiva) + 10.0, 100.0))
do_requerido = do_crit_basal * sda_multiplier

# 4. Decisión de Negocio
if do_efectivo >= do_requerido:
    racion_autorizada = racion_propuesta
    estado = "✅ SÍNTESIS ÓPTIMA"
    color = "green"
    alerta = "El ambiente soporta la asimilación de macronutrientes. Alimentación autorizada."
else:
    factor = do_efectivo / do_requerido
    racion_autorizada = racion_propuesta * factor
    estado = "🛑 RIESGO DE ASFIXIA POST-PRANDIAL"
    color = "red"
    alerta = f"Oxígeno insuficiente ({do_efectivo:.1f}%) para procesar una dieta de {pct_proteina}% de proteína. Bloqueo preventivo activado."

kg_salvados = racion_propuesta - racion_autorizada
roi_usd = kg_salvados * precio_alimento

# --- RENDERIZADO DEL DASHBOARD ---
col1, col2, col3 = st.columns(3)
col1.metric("Profundidad del Cardumen", f"{prof_optima:.1f} m", f"Temp: {temp_efectiva:.1f} °C")
col2.metric("Multiplicador SDA (Macro)", f"{sda_multiplier:.2f}x", f"DO Req: {do_requerido:.1f}%", delta_color="inverse")
col3.metric("Ahorro Financiero (ROI)", f"${roi_usd:,.0f} USD", f"{kg_salvados:,.0f} kg bloqueados")

st.markdown("---")
st.subheader(f"Veredicto del Motor: {estado}")
st.info(alerta)

# Gráficos
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(temp_array, z_array, 'r-', linewidth=2, label='Temp Interpolada (°C)')
ax.plot(do_array, z_array, 'b-', linewidth=2, label='DO Interpolado (%)')
ax.axhline(prof_optima, color='green', linestyle='--', label=f'Hábitat Pez ({prof_optima:.1f}m)')
ax.axvline(do_requerido, color='black', linestyle=':', label=f'Límite Asfixia SDA ({do_requerido:.1f}%)')
ax.invert_yaxis()
ax.set_ylabel("Profundidad (m)")
ax.legend()
ax.grid(alpha=0.3)

st.pyplot(fig)
