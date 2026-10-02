import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
import requests

st.set_page_config(page_title="SalmonFeed SaaS", layout="wide")
st.title("🐟 SalmonFeed - Optimizador Metabólico B2B")
st.markdown("Motor predictivo con 'Sombra de Oxígeno' (Biomasa + Fouling) y conexión a API oceanográfica satelital.")

# --- MÓDULOS DEL MOTOR ---
class EntornoHidrodinamico:
    @staticmethod
    def generar_gemelo_digital(t_sup, do_sup, t_fon, do_fon, biomasa_kg, mo2_basal_mg_kg_h, vel_corriente_m_s, fouling_pct):
        profundidades = [1, 15]
        temps = [t_sup, t_fon]
        dos = [do_sup, do_fon]
        z_array = np.linspace(1, 15, 50)
        temp_array = PchipInterpolator(profundidades, temps)(z_array)
        do_base_array = np.clip(PchipInterpolator(profundidades, dos)(z_array), 0, 100)
        
        idx_opt = np.argmin(np.abs(temp_array - 13.5))
        
        flujo_efectivo = vel_corriente_m_s * (1.0 - (fouling_pct / 100.0))
        consumo_total_mg_h = biomasa_kg * mo2_basal_mg_kg_h
        
        # Penalidad de oxígeno por la biomasa respirando
        penalty_do_pct = min((consumo_total_mg_h / (flujo_efectivo * 1000000)) * 0.05, 30.0)
        
        sigma = 1.5 
        do_real_array = do_base_array.copy()
        for i, z in enumerate(z_array):
            distancia_al_centro = abs(z - z_array[idx_opt])
            caida = penalty_do_pct * np.exp(-0.5 * (distancia_al_centro / sigma)**2)
            do_real_array[i] = max(0, do_real_array[i] - caida)
            
        return z_array, temp_array, do_base_array, do_real_array, idx_opt

class FisiologiaHvas:
    @staticmethod
    def calcular_mo2_basal(peso_kg, temp_c, vel_natacion_bl_s):
        return 79.7 * (peso_kg ** -0.14) * (1.04 ** temp_c) * (1.63 ** vel_natacion_bl_s)

class SDA_Nutricional:
    @staticmethod
    def multiplicador_macronutrientes(pct_prot, pct_lip, pct_carb):
        costo_dieta = (pct_prot * 0.25) + (pct_lip * 0.04) + (pct_carb * 0.12)
        costo_estandar = (45 * 0.25) + (28 * 0.04) + (12 * 0.12)
        return 1.0 + (0.4 * (costo_dieta / costo_estandar))

class SateliteOceanografico:
    @staticmethod
    def obtener_temperatura_real(latitud, longitud):
        try:
            url = f"https://marine-api.open-meteo.com/v1/marine?latitude={latitud}&longitude={longitud}&current=ocean_temperature"
            respuesta = requests.get(url)
            datos = respuesta.json()
            temp_real = datos['current']['ocean_temperature']
            return temp_real
        except:
            return None

# --- INTERFAZ SIDEBAR ---
st.sidebar.header("1. Jaula y Dinámica")
biomasa_kg = st.sidebar.number_input("Biomasa Total (kg)", value=150000, step=10000)
vel_corriente = st.sidebar.slider("Corriente (m/s)", 0.01, 0.50, 0.15)
fouling = st.sidebar.slider("% Suciedad Red (Fouling)", 0, 80, 30)
peso_pez = st.sidebar.number_input("Peso Promedio Pez (kg)", value=2.5, step=0.5)
racion = st.sidebar.number_input("Ración a Disparar (kg)", value=1500, step=100)

st.sidebar.header("2. Dieta Proximal")
pct_prot = st.sidebar.slider("% Proteína Cruda", 30.0, 60.0, 46.5)
pct_lip = st.sidebar.slider("% Lípidos", 15.0, 40.0, 28.0)
pct_carb = st.sidebar.slider("% Carbohidratos", 5.0, 25.0, 12.0)

st.sidebar.header("3. Telemetría y APIs")
usar_api = st.sidebar.checkbox("📡 Conectar a Océano Real (API Satelital)")

if usar_api:
    ubicacion = st.sidebar.selectbox("Seleccionar Centro de Cultivo", ["Matre, Noruega", "Puerto Montt, Chile"])
    if ubicacion == "Matre, Noruega":
        lat, lon = 60.87, 5.58
    else:
        lat, lon = -41.47, -72.93
        
    temp_satelite = SateliteOceanografico.obtener_temperatura_real(lat, lon)
    
    if temp_satelite:
        st.sidebar.success(f"Conexión en vivo. Temp actual en {ubicacion}: {temp_satelite}°C")
        t_sup = temp_satelite
        t_fon = temp_satelite - 3.5 
    else:
        st.sidebar.error("Error conectando a la API satelital. Usando datos por defecto.")
        t_sup = 14.5
        t_fon = 10.0
else:
    st.sidebar.info("Modo Manual Activo")
    t_sup = st.sidebar.number_input("Temp Superficie (°C)", value=14.5)
    t_fon = st.sidebar.number_input("Temp Fondo 15m (°C)", value=10.0)

do_sup = st.sidebar.number_input("DO Superficie (%)", value=85.0)
do_fon = st.sidebar.number_input("DO Fondo 15m (%)", value=60.0)

# --- EJECUCIÓN DEL MOTOR ---
mo2_basal_ini = FisiologiaHvas.calcular_mo2_basal(peso_pez, 13.5, 0.5)

z_array, t_array, do_base, do_real, idx_opt = EntornoHidrodinamico.generar_gemelo_digital(
    t_sup, do_sup, t_fon, do_fon, biomasa_kg, mo2_basal_ini, vel_corriente, fouling
)

prof_opt = z_array[idx_opt]
temp_pez = t_array[idx_opt]
do_real_pez = do_real[idx_opt]
do_ambiente_limpio = do_base[idx_opt] 

mo2_basal = FisiologiaHvas.calcular_mo2_basal(peso_pez, temp_pez, 0.5)
sda_mult = SDA_Nutricional.multiplicador_macronutrientes(pct_prot, pct_lip, pct_carb)
mo2_postprandial = mo2_basal * sda_mult

do_req_basal = max(30.0, min((3.75 * temp_pez) + 10.0, 100.0))
do_req_total = do_req_basal * sda_mult

if do_real_pez >= do_req_total:
    estado, color, r_final = "✅ ALIMENTAR (CAPACIDAD SOPORTADA)", "green", racion
else:
    factor = do_real_pez / do_req_total
    r_final = racion * factor
    estado, color = "🛑 BLOQUEO PREVENTIVO ACTIVADO", "red"

kg_salvados = racion - r_final
roi_usd = kg_salvados * 1.8

# --- DASHBOARD VISUAL ---
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Hábitat Pez", f"{prof_opt:.1f} m", f"DO Real: {do_real_pez:.1f}%")
col2.metric("Límite Asfixia (SDA)", f"{do_req_total:.1f}% DO Req", f"MO2 Post-Comida: {mo2_postprandial:.0f} mg/kg/h", delta_color="inverse")
col3.metric("Impacto Financiero", f"${roi_usd:,.0f} USD Salvados", f"{kg_salvados:,.0f} kg Bloqueados")

st.subheader(estado)
st.write(f"**Diagnóstico de Software:** Si operáramos con sensores tradicionales a ciegas, creeríamos que el oxígeno es de **{do_ambiente_limpio:.1f}%** (suficiente). Sin embargo, nuestro algoritmo detecta que el 'Efecto Sumidero' generado por **{biomasa_kg:,.0f} kg** de biomasa respirando, sumado a un bloqueo de flujo por fouling del **{fouling}%**, desplomó el oxígeno real del cardumen a **{do_real_pez:.1f}%**.")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(t_array, z_array, 'r-', linewidth=2, label='Temperatura (°C)')
ax.plot(do_base, z_array, 'b--', linewidth=1.5, alpha=0.5, label='DO Teórico (Agua Limpia)')
ax.plot(do_real, z_array, 'b-', linewidth=3, label='DO REAL (Sombra de Oxígeno)')
ax.axhline(prof_opt, color='green', linestyle=':', label=f'Cardumen ({prof_opt:.1f}m)')
ax.axvline(do_req_total, color='black', linestyle='-.', label=f'Umbral de Asfixia SDA ({do_req_total:.1f}%)')
ax.invert_yaxis()
ax.set_ylabel("Profundidad (m)")
ax.set_xlabel("Valor (°C o % DO)")
ax.legend()
ax.grid(alpha=0.3)
st.pyplot(fig)
