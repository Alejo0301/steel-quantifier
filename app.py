"""
app.py  —  Cuantificador de Acero v2.1
Ejecutar con:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io, os, tempfile
from collections import defaultdict

from parser import parsear_archivo
from parser_dxf import parsear_dxf
from generador_pdf import generar_pdf, generar_pdf_combinado


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIONES CACHEADAS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_vigas(file_bytes, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    tabla_nsr, vigas = parsear_archivo(tmp_path)
    os.unlink(tmp_path)
    return tabla_nsr, vigas

@st.cache_data
def cargar_columnas(file_bytes, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf", mode="wb") as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    tabla_nsr, cols = parsear_dxf(tmp_path)
    os.unlink(tmp_path)
    return tabla_nsr, cols


# ─────────────────────────────────────────────────────────────────────────────
#  INICIALIZAR SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "reset_txt" not in st.session_state: st.session_state["reset_txt"] = 0
if "reset_dxf" not in st.session_state: st.session_state["reset_dxf"] = 0

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Cuantificador de Acero", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

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
    st.markdown("#### 📂 Vigas (.txt)")
    uploaded_txt = st.file_uploader("Archivo despiece vigas", type=["txt"], key=f"up_txt_{st.session_state['reset_txt']}")
    st.markdown("#### 📐 Columnas (.dxf)")
    uploaded_dxf = st.file_uploader("Archivo DXF columnas", type=["dxf","DXF"], key=f"up_dxf_{st.session_state['reset_dxf']}")
    st.markdown("---")
    st.caption("v2.1 — NSR-10 Colombia")


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style='margin:0'>🏗️ Cuantificador de Acero — NSR-10</h2>
    <p style='margin:0; opacity:0.8; font-size:0.9rem'>
        Carga el .txt de vigas y/o el .dxf de columnas para cuantificar y generar PDFs
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  GUARD
# ─────────────────────────────────────────────────────────────────────────────
if uploaded_txt is None and uploaded_dxf is None:
    st.info("👈 Sube un **.txt** de vigas y/o un **.dxf** de columnas para comenzar.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📂 Vigas (.txt)**\n1. Sube el `.txt` de despiece\n2. Revisa la tabla\n3. Genera el PDF")
    with c2:
        st.markdown("**📐 Columnas (.dxf)**\n1. Sube el `.dxf` de despiece\n2. El parser lee barras y estribos\n3. Genera el PDF")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  PARSEO
# ─────────────────────────────────────────────────────────────────────────────
vigas_txt    = []
columnas_dxf = []
tabla_nsr    = {}

if uploaded_txt:
    with st.spinner("Procesando vigas…"):
        tabla_nsr, vigas_txt = cargar_vigas(uploaded_txt.getvalue(), uploaded_txt.name)
    if not vigas_txt:
        st.error("No se encontraron vigas en el .txt.")

if uploaded_dxf:
    with st.spinner("Procesando columnas DXF…"):
        tabla_dxf, columnas_dxf = cargar_columnas(uploaded_dxf.getvalue(), uploaded_dxf.name)
        if not tabla_nsr: tabla_nsr = tabla_dxf
    if not columnas_dxf:
        st.error("No se encontraron columnas en el .dxf.")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: render tabla + resumen + PDF de una sección
# ─────────────────────────────────────────────────────────────────────────────
def render_seccion(elementos, tabla, etiqueta, tab):
    with tab:
        total_unicos = len(set(v["nombre"] for v in elementos))
        peso_gral    = sum(v["peso_total"] for v in elementos)
        total_barras = sum(len(v["barras"]) for v in elementos)
        ubicaciones  = sorted({v["ubicacion"] for v in elementos})

        c1,c2,c3,c4 = st.columns(4)
        c1.metric(f"Total {etiqueta}", total_unicos)
        c2.metric("Total elementos",  total_barras)
        c3.metric("Peso total (kg)",  f"{peso_gral:.2f}")
        c4.metric("Peso total (ton)", f"{peso_gral/1000:.4f}")
        st.markdown("---")

        st.subheader("📋 Tabla de cuantificación")
        cf1,cf2 = st.columns(2)
        filtro_ubic = cf1.multiselect("Ubicación", ubicaciones, default=ubicaciones, key=f"ubic_{etiqueta}")
        filtro_diam = cf2.multiselect("Diámetro",  sorted(tabla.keys()), default=list(tabla.keys()), key=f"diam_{etiqueta}")

        rows = []; item = 1
        for vp in elementos:
            if vp["ubicacion"] not in filtro_ubic: continue
            for e in vp["barras"]:
                if e["diametro"] not in filtro_diam: continue
                if e["tipo"] == "BARRA":
                    desc = f"Barra {e['diametro']}  L={e['longitud']:.2f}m" \
                           + (f"  G.izq={e['gancho_izq']:.2f}" if e.get('gancho_izq') else "") \
                           + (f"  G.der={e['gancho_der']:.2f}" if e.get('gancho_der') else "")
                elif e["tipo"] == "ESTRIBO":
                    desc = f"Estribo {e['diametro']}  {e.get('base',0):.2f}x{e.get('altura',0):.2f}m"
                else:
                    desc = f"Gancho {e['diametro']}  L={e.get('base',0):.2f}m"
                rows.append({
                    "Item": f"{item:04d}", etiqueta: vp["nombre"],
                    "Ubicación": vp["ubicacion"], "Tipo": e["tipo"],
                    "Descripción": desc, "Cant.": e["cantidad"],
                    "Diámetro": e["diametro"], "L.Total(m)": e["longitud_total"],
                    "P.Unit(kg)": e["peso_unit"], "P.Total(kg)": e["peso_total"],
                })
                item += 1

        df = pd.DataFrame(rows)
        if df.empty:
            st.warning("Sin elementos con los filtros seleccionados.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True,
                column_config={
                    "P.Total(kg)": st.column_config.NumberColumn(format="%.3f"),
                    "P.Unit(kg)":  st.column_config.NumberColumn(format="%.3f"),
                    "L.Total(m)":  st.column_config.NumberColumn(format="%.3f"),
                })
            st.caption(f"{len(df)} elementos — Peso filtrado: {df['P.Total(kg)'].sum():.2f} kg")

        # Resumen por diámetro
        st.markdown("---")
        st.subheader("📊 Resumen por diámetro")
        rd = defaultdict(float)
        for v in elementos:
            for e in v["barras"]: rd[e["diametro"]] += e["peso_total"]
        df_r = pd.DataFrame([
            {"Diámetro": k, "Peso (kg)": round(v,2), "Peso (ton)": round(v/1000,4)}
            for k,v in sorted(rd.items(), key=lambda x: int(x[0].replace("#","").replace("BAJA","0")))
        ])
        tot = df_r["Peso (kg)"].sum()
        df_r.loc[len(df_r)] = ["TOTAL", round(tot,2), round(tot/1000,4)]
        cr1,cr2 = st.columns([1,2])
        with cr1: st.dataframe(df_r, use_container_width=True, hide_index=True)
        with cr2:
            st.bar_chart(df_r[df_r["Diámetro"]!="TOTAL"].set_index("Diámetro")["Peso (kg)"],
                         use_container_width=True)

        # PDF individual
        st.markdown("---")
        st.subheader("📄 Generar PDF")
        cp1,cp2 = st.columns([2,1])
        with cp1:
            st.markdown("PDF con tabla de elementos, diagramas y resumen por diámetro.")
        with cp2:
            if st.button(f"🖨️ PDF {etiqueta}", type="primary",
                         use_container_width=True, key=f"btn_{etiqueta}"):
                with st.spinner("Generando PDF…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp_pdf = tmp.name
                    generar_pdf(elementos, tmp_pdf, proyecto=f"{proyecto} — {etiqueta}")
                    pdf_bytes = open(tmp_pdf,"rb").read()
                    os.unlink(tmp_pdf)
                st.success("✅ PDF listo")
                st.download_button("⬇️ Descargar PDF", pdf_bytes,
                    file_name=f"Cuantificacion_{etiqueta}_{proyecto.replace(' ','_')}.pdf",
                    mime="application/pdf", use_container_width=True, key=f"dl_{etiqueta}")

        # Botón borrar sección
        st.markdown("---")
        reset_key = "reset_txt" if etiqueta == "Vigas" else "reset_dxf"
        if st.button(f"🗑️ Borrar {etiqueta}", use_container_width=True,
                     key=f"borrar_{etiqueta}"):
            st.session_state[reset_key] += 1
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_labels = []
if vigas_txt:    tab_labels.append("🧱 Vigas")
if columnas_dxf: tab_labels.append("🏛️ Columnas")
if vigas_txt and columnas_dxf: tab_labels.append("📊 Resumen General")

if not tab_labels:
    st.warning("No se pudo procesar ningún archivo.")
    st.stop()

tabs = st.tabs(tab_labels)
idx  = 0

if vigas_txt:
    render_seccion(vigas_txt, tabla_nsr, "Vigas", tabs[idx]); idx += 1

if columnas_dxf:
    render_seccion(columnas_dxf, tabla_nsr, "Columnas", tabs[idx]); idx += 1

# ── Tab Resumen General ──────────────────────────────────────────────────────
if vigas_txt and columnas_dxf:
    with tabs[idx]:
        st.subheader("📊 Resumen General del Proyecto")

        # Métricas globales
        peso_vigas = sum(v["peso_total"] for v in vigas_txt)
        peso_cols  = sum(v["peso_total"] for v in columnas_dxf)
        peso_total = peso_vigas + peso_cols

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Peso Vigas (kg)",    f"{peso_vigas:.2f}")
        c2.metric("Peso Columnas (kg)", f"{peso_cols:.2f}")
        c3.metric("Peso Total (kg)",    f"{peso_total:.2f}")
        c4.metric("Peso Total (ton)",   f"{peso_total/1000:.4f}")

        st.markdown("---")

        # Tabla combinada por diámetro
        rd_v = defaultdict(float)
        rd_c = defaultdict(float)
        rd_l = defaultdict(float)
        rd_n = defaultdict(int)

        for v in vigas_txt:
            for e in v["barras"]:
                rd_v[e["diametro"]] += e["peso_total"]
                rd_l[e["diametro"]] += e["longitud_total"] * e["cantidad"]
                rd_n[e["diametro"]] += e["cantidad"]
        for v in columnas_dxf:
            for e in v["barras"]:
                rd_c[e["diametro"]] += e["peso_total"]
                rd_l[e["diametro"]] += e["longitud_total"] * e["cantidad"]
                rd_n[e["diametro"]] += e["cantidad"]

        diams = sorted(set(list(rd_v.keys()) + list(rd_c.keys())),
                       key=lambda x: int(x.replace("#","").replace("BAJA","0")))

        rows_comb = []
        for d in diams:
            pt = rd_v[d] + rd_c[d]
            rows_comb.append({
                "Diámetro":        d,
                "N° Barras":       rd_n[d],
                "Long. Acum. (m)": round(rd_l[d], 2),
                "Vigas (kg)":      round(rd_v[d], 2),
                "Columnas (kg)":   round(rd_c[d], 2),
                "Total (kg)":      round(pt, 2),
                "Total (ton)":     round(pt/1000, 4),
            })

        df_comb = pd.DataFrame(rows_comb)
        total_row = {
            "Diámetro": "TOTAL",
            "N° Barras": df_comb["N° Barras"].sum(),
            "Long. Acum. (m)": round(df_comb["Long. Acum. (m)"].sum(), 2),
            "Vigas (kg)": round(df_comb["Vigas (kg)"].sum(), 2),
            "Columnas (kg)": round(df_comb["Columnas (kg)"].sum(), 2),
            "Total (kg)": round(df_comb["Total (kg)"].sum(), 2),
            "Total (ton)": round(df_comb["Total (ton)"].sum(), 4),
        }
        df_comb = pd.concat([df_comb, pd.DataFrame([total_row])], ignore_index=True)

        st.dataframe(df_comb, use_container_width=True, hide_index=True,
            column_config={
                "Total (kg)":      st.column_config.NumberColumn(format="%.2f"),
                "Vigas (kg)":      st.column_config.NumberColumn(format="%.2f"),
                "Columnas (kg)":   st.column_config.NumberColumn(format="%.2f"),
                "Long. Acum. (m)": st.column_config.NumberColumn(format="%.2f"),
                "Total (ton)":     st.column_config.NumberColumn(format="%.4f"),
            })

        # Gráfico combinado
        st.markdown("---")
        st.subheader("📈 Distribución de peso por diámetro")
        df_graf = df_comb[df_comb["Diámetro"] != "TOTAL"].set_index("Diámetro")[["Vigas (kg)", "Columnas (kg)"]]
        st.bar_chart(df_graf, use_container_width=True)

        # PDF combinado completo
        st.markdown("---")
        st.subheader("📄 PDF Completo del Proyecto")
        gp1,gp2 = st.columns([2,1])
        with gp1:
            st.markdown("""
El PDF completo incluye:
- **Sección Vigas** — tabla de elementos + resumen por diámetro
- **Sección Columnas** — tabla de elementos + resumen por diámetro
- **Resumen Ponderado Final** — todos los diámetros, vigas vs columnas, totales
            """)
        with gp2:
            if st.button("🖨️ PDF Proyecto Completo", type="primary",
                         use_container_width=True, key="btn_comb"):
                with st.spinner("Generando PDF completo…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp_pdf = tmp.name
                    generar_pdf_combinado(vigas_txt, columnas_dxf, tmp_pdf, proyecto=proyecto)
                    pdf_bytes = open(tmp_pdf,"rb").read()
                    os.unlink(tmp_pdf)
                st.success("✅ PDF completo listo")
                st.download_button("⬇️ Descargar PDF Completo", pdf_bytes,
                    file_name=f"Proyecto_Completo_{proyecto.replace(' ','_')}.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_comb")