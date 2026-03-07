"""
app.py  —  Cuantificador de Acero v2.0
Ejecutar con:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io, os, tempfile
from collections import defaultdict

from parser import parsear_archivo
from parser_dxf import parsear_dxf
from generador_pdf import generar_pdf


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIONES CACHEADAS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_vigas(file_bytes, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    tabla_nsr, vigas = parsear_archivo(tmp_path)
    os.unlink(tmp_path)
    return tabla_nsr, vigas


@st.cache_data
def cargar_columnas(file_bytes, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf", mode="wb") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    tabla_nsr, columnas = parsear_dxf(tmp_path)
    os.unlink(tmp_path)
    return tabla_nsr, columnas


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
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 6px 6px 0 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ Cuantificador de Acero")
    st.markdown("---")
    proyecto = st.text_input("Nombre del proyecto", value="TRINIDAD CASA 2")

    st.markdown("#### 📂 Vigas (.txt)")
    uploaded_txt = st.file_uploader(
        "Archivo de despiece de vigas",
        type=["txt"],
        help="Archivo .txt generado por el programa de figuración",
        key="uploader_txt"
    )

    st.markdown("#### 📐 Columnas (.dxf)")
    uploaded_dxf = st.file_uploader(
        "Archivo DXF de despiece de columnas",
        type=["dxf", "DXF"],
        help="Archivo .dxf generado por el programa de despiece",
        key="uploader_dxf"
    )

    st.markdown("---")
    st.caption("v2.0 — NSR-10 Colombia")


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style='margin:0'>🏗️ Cuantificador de Acero — NSR-10</h2>
    <p style='margin:0; opacity:0.8; font-size:0.9rem'>
        Carga tu archivo .txt de vigas y/o el .dxf de columnas para generar el PDF de cuantificación
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  GUARD: sin ningún archivo
# ─────────────────────────────────────────────────────────────────────────────
if uploaded_txt is None and uploaded_dxf is None:
    st.info("👈 Sube un archivo **.txt** de vigas y/o un **.dxf** de columnas para comenzar.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**📂 Vigas (.txt)**
1. Sube el `.txt` de despiece de vigas
2. Revisa la tabla con todos los elementos
3. Genera el PDF de cuantificación
        """)
    with col2:
        st.markdown("""
**📐 Columnas (.dxf)**
1. Sube el `.dxf` de despiece de columnas
2. El parser lee automáticamente barras y estribos
3. Genera el PDF con el mismo formato profesional
        """)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  PARSEO DE ARCHIVOS
# ─────────────────────────────────────────────────────────────────────────────
vigas_txt    = []
columnas_dxf = []
tabla_nsr    = {}

if uploaded_txt is not None:
    with st.spinner("Procesando archivo de vigas…"):
        tabla_nsr, vigas_txt = cargar_vigas(uploaded_txt.getvalue(), uploaded_txt.name)
    if not vigas_txt:
        st.error("No se encontraron vigas en el archivo .txt. Verifica el formato.")

if uploaded_dxf is not None:
    with st.spinner("Procesando archivo DXF de columnas…"):
        tabla_dxf, columnas_dxf = cargar_columnas(uploaded_dxf.getvalue(), uploaded_dxf.name)
        if not tabla_nsr:
            tabla_nsr = tabla_dxf
    if not columnas_dxf:
        st.error("No se encontraron columnas en el archivo .dxf. Verifica el formato.")


# ─────────────────────────────────────────────────────────────────────────────
#  TABS: Vigas / Columnas
# ─────────────────────────────────────────────────────────────────────────────
tabs_labels = []
if vigas_txt:    tabs_labels.append("🧱 Vigas")
if columnas_dxf: tabs_labels.append("🏛️ Columnas")

if not tabs_labels:
    st.warning("No se pudo procesar ningún archivo.")
    st.stop()

tabs = st.tabs(tabs_labels)
tab_idx = 0


# ── Helper: render sección de cuantificación ─────────────────────────────────
def render_seccion(elementos, tabla, etiqueta_elemento, tab):
    with tab:
        peso_total_general = sum(v["peso_total"] for v in elementos)
        total_barras       = sum(len(v["barras"]) for v in elementos)
        ubicaciones        = sorted({v["ubicacion"] for v in elementos})

        c1, c2, c3, c4 = st.columns(4)
        total_unicos = len(set(v['nombre'] for v in elementos))
        c1.metric(f"Total {etiqueta_elemento}", total_unicos)
        c2.metric("Total elementos",  total_barras)
        c3.metric("Peso total (kg)",  f"{peso_total_general:.2f}")
        c4.metric("Peso total (ton)", f"{peso_total_general/1000:.4f}")

        st.markdown("---")
        st.subheader("📋 Tabla de cuantificación")

        cf1, cf2 = st.columns(2)
        filtro_ubic = cf1.multiselect(
            "Filtrar por ubicación",
            options=ubicaciones, default=ubicaciones,
            key=f"ubic_{etiqueta_elemento}"
        )
        filtro_diam = cf2.multiselect(
            "Filtrar por diámetro",
            options=sorted(tabla.keys()),
            default=list(tabla.keys()),
            key=f"diam_{etiqueta_elemento}"
        )

        rows = []
        item = 1
        for elem_padre in elementos:
            if elem_padre["ubicacion"] not in filtro_ubic:
                continue
            for elem in elem_padre["barras"]:
                if elem["diametro"] not in filtro_diam:
                    continue
                if elem["tipo"] == "BARRA":
                    desc = (
                        f"Barra {elem['diametro']}  L={elem['longitud']:.2f}m"
                        + (f"  G.izq={elem['gancho_izq']:.2f}" if elem.get('gancho_izq') else "")
                        + (f"  G.der={elem['gancho_der']:.2f}" if elem.get('gancho_der') else "")
                    )
                elif elem["tipo"] == "ESTRIBO":
                    desc = f"Estribo {elem['diametro']}  {elem.get('base',0):.2f}x{elem.get('altura',0):.2f}m"
                else:
                    desc = f"Gancho {elem['diametro']}  L={elem.get('base',0):.2f}m"

                rows.append({
                    "Item":        f"{item:04d}",
                    etiqueta_elemento: elem_padre["nombre"],
                    "Ubicación":   elem_padre["ubicacion"],
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

        # Resumen por diámetro
        st.markdown("---")
        st.subheader("📊 Resumen por diámetro")
        resumen_diam = defaultdict(float)
        for v in elementos:
            for e in v["barras"]:
                resumen_diam[e["diametro"]] += e["peso_total"]

        df_res = pd.DataFrame([
            {"Diámetro": k, "Peso Total (kg)": round(v, 2), "Peso Total (ton)": round(v/1000, 4)}
            for k, v in sorted(resumen_diam.items(),
                               key=lambda x: int(x[0].replace("#","").replace("BAJA","0")))
        ])
        total_kg = df_res["Peso Total (kg)"].sum()
        df_res.loc[len(df_res)] = ["TOTAL", round(total_kg, 2), round(total_kg/1000, 4)]

        cr1, cr2 = st.columns([1, 2])
        with cr1:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        with cr2:
            st.bar_chart(
                df_res[df_res["Diámetro"] != "TOTAL"].set_index("Diámetro")["Peso Total (kg)"],
                use_container_width=True
            )

        # Generar PDF
        st.markdown("---")
        st.subheader("📄 Generar PDF")
        cp1, cp2 = st.columns([2, 1])
        with cp1:
            st.markdown("""
El PDF incluye tabla con diagramas, cantidades, pesos y hoja de resumen por diámetro.
            """)
        with cp2:
            if st.button("🖨️ Generar PDF", type="primary",
                         use_container_width=True, key=f"btn_pdf_{etiqueta_elemento}"):
                with st.spinner("Generando PDF con diagramas…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp_pdf = tmp.name
                    titulo = f"{proyecto} — {etiqueta_elemento}"
                    generar_pdf(elementos, tmp_pdf, proyecto=titulo)
                    with open(tmp_pdf, "rb") as f:
                        pdf_bytes = f.read()
                    os.unlink(tmp_pdf)

                st.success("✅ PDF generado exitosamente")
                nombre_pdf = f"Cuantificacion_{etiqueta_elemento}_{proyecto.replace(' ','_')}.pdf"
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=nombre_pdf,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{etiqueta_elemento}"
                )


# ─────────────────────────────────────────────────────────────────────────────
#  RENDERIZAR TABS
# ─────────────────────────────────────────────────────────────────────────────
if vigas_txt:
    render_seccion(vigas_txt, tabla_nsr, "Vigas", tabs[tab_idx])
    tab_idx += 1

if columnas_dxf:
    render_seccion(columnas_dxf, tabla_nsr, "Columnas", tabs[tab_idx])