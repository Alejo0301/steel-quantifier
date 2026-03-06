"""
app.py  —  Cuantificador de Acero v1.0
Ejecutar con:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io, os, tempfile
from collections import defaultdict

from parser import parsear_archivo
from generador_pdf import generar_pdf


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN CACHEADA — debe estar ANTES de cualquier widget o st.stop()
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos(file_bytes, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    tabla_nsr, vigas = parsear_archivo(tmp_path)
    os.unlink(tmp_path)
    return tabla_nsr, vigas


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cuantificador de Acero",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: white; padding: 1.2rem 1.5rem; border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stDataFrame"] { width: 100% !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ Cuantificador de Acero")
    st.markdown("---")
    proyecto = st.text_input("Nombre del proyecto", value="TRINIDAD CASA 2")
    uploaded = st.file_uploader(
        "📂 Subir archivo .txt de despiece",
        type=["txt"],
        help="Archivo generado por el programa de figuración"
    )
    st.markdown("---")
    st.caption("v1.0 — NSR-10 Colombia")


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style='margin:0'>🏗️ Cuantificador de Acero — NSR-10</h2>
    <p style='margin:0; opacity:0.8; font-size:0.9rem'>
        Carga tu archivo .txt de despiece y genera el PDF de cuantificación
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  GUARD: sin archivo → pantalla de bienvenida
# ─────────────────────────────────────────────────────────────────────────────
if uploaded is None:
    st.info("👈 Sube tu archivo **.txt** de despiece en el panel izquierdo para comenzar.")
    st.markdown("""
    ### ¿Cómo funciona?
    1. **Sube** el archivo `.txt` generado por tu programa de despiece
    2. **Revisa** la tabla interactiva con todos los elementos
    3. **Genera** el PDF profesional con diagramas y cantidades
    """)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  PARSEO — solo se ejecuta cuando hay archivo
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Procesando archivo…"):
    tabla_nsr, vigas = cargar_datos(uploaded.getvalue(), uploaded.name)

if not vigas:
    st.error("No se encontraron vigas en el archivo. Verifica el formato.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  MÉTRICAS GENERALES
# ─────────────────────────────────────────────────────────────────────────────
peso_total_general = sum(v["peso_total"] for v in vigas)
total_barras       = sum(len(v["barras"]) for v in vigas)
ubicaciones        = sorted({v["ubicacion"] for v in vigas})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total vigas",      len(vigas))
col2.metric("Total elementos",  total_barras)
col3.metric("Peso total (kg)",  f"{peso_total_general:.2f}")
col4.metric("Peso total (ton)", f"{peso_total_general/1000:.4f}")

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA INTERACTIVA
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📋 Tabla de cuantificación")

col_f1, col_f2 = st.columns(2)
filtro_ubic = col_f1.multiselect(
    "Filtrar por ubicación", options=ubicaciones, default=ubicaciones
)
filtro_diam = col_f2.multiselect(
    "Filtrar por diámetro",
    options=sorted(tabla_nsr.keys()),
    default=list(tabla_nsr.keys())
)

rows = []
item = 1
for viga in vigas:
    if viga["ubicacion"] not in filtro_ubic:
        continue
    for elem in viga["barras"]:
        if elem["diametro"] not in filtro_diam:
            continue
        if elem["tipo"] == "BARRA":
            desc = (
                f"Barra {elem['diametro']}  L={elem['longitud']:.2f}m"
                + (f"  G.izq={elem['gancho_izq']:.2f}" if elem['gancho_izq'] else "")
                + (f"  G.der={elem['gancho_der']:.2f}" if elem['gancho_der'] else "")
            )
        elif elem["tipo"] == "ESTRIBO":
            desc = f"Estribo {elem['diametro']}  {elem['base']:.2f}x{elem['altura']:.2f}m  G135={elem['gancho_val']:.2f}"
        else:
            desc = f"Gancho {elem['diametro']}  L={elem['base']:.2f}m"

        rows.append({
            "Item":        f"{item:04d}",
            "Viga":        viga["nombre"],
            "Ubicación":   viga["ubicacion"],
            "Tipo":        elem["tipo"],
            "Descripción": desc,
            "Cant.":       elem["cantidad"],
            "Diámetro":    elem["diametro"],
            "L.Total(m)":  elem["longitud_total"],
            "P.Unit(kg)":  elem["peso_unit"],
            "P.Total(kg)": elem["peso_total"],
        })
        item += 1

df = pd.DataFrame(rows)

if df.empty:
    st.warning("No hay elementos con los filtros seleccionados.")
else:
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "P.Total(kg)": st.column_config.NumberColumn(format="%.3f"),
            "P.Unit(kg)":  st.column_config.NumberColumn(format="%.3f"),
            "L.Total(m)":  st.column_config.NumberColumn(format="%.3f"),
        }
    )
    st.caption(f"Mostrando {len(df)} elementos — Peso filtrado: {df['P.Total(kg)'].sum():.2f} kg")


# ─────────────────────────────────────────────────────────────────────────────
#  RESUMEN POR DIÁMETRO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Resumen por diámetro")

resumen_diam = defaultdict(float)
for viga in vigas:
    for elem in viga["barras"]:
        resumen_diam[elem["diametro"]] += elem["peso_total"]

df_res = pd.DataFrame([
    {"Diámetro": k, "Peso Total (kg)": round(v, 2), "Peso Total (ton)": round(v / 1000, 4)}
    for k, v in sorted(resumen_diam.items(),
                       key=lambda x: int(x[0].replace("#", "").replace("BAJA", "0")))
])
total_kg = df_res["Peso Total (kg)"].sum()
df_res.loc[len(df_res)] = ["TOTAL", round(total_kg, 2), round(total_kg / 1000, 4)]

col_r1, col_r2 = st.columns([1, 2])
with col_r1:
    st.dataframe(df_res, use_container_width=True, hide_index=True)
with col_r2:
    st.bar_chart(
        df_res[df_res["Diámetro"] != "TOTAL"].set_index("Diámetro")["Peso Total (kg)"],
        use_container_width=True
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GENERACIÓN DEL PDF
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📄 Generar PDF")

col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    st.markdown("""
El PDF incluye:
- **Encabezado** con nombre del proyecto y fecha
- **Tabla por viga** con: item, diagrama, cantidad, diámetro, longitud, pesos y ubicación
- **Hoja de resumen** con totales por diámetro
    """)

with col_p2:
    if st.button("🖨️ Generar PDF", type="primary", use_container_width=True):
        with st.spinner("Generando PDF con diagramas…"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp_pdf = tmp.name
            generar_pdf(vigas, tmp_pdf, proyecto=proyecto)
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_pdf)

        st.success("✅ PDF generado exitosamente")
        nombre_pdf = f"Cuantificacion_Acero_{proyecto.replace(' ', '_')}.pdf"
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=nombre_pdf,
            mime="application/pdf",
            use_container_width=True
        )