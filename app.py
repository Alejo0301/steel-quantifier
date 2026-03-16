"""
app.py  —  Cuantificador de Acero v3.0
Ejecutar con:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io, os, tempfile
from collections import defaultdict

from parser import parsear_archivo
from parser_dxf import parsear_dxf
from generador_pdf import generar_pdf, generar_pdf_combinado
from catalogos import (
    BARRAS_NSR10, LISTA_DIAMETROS, GANCHOS_BARRA,
    DIMENSIONES_ESTRIBOS, MALLAS, LISTA_MALLAS,
    GANCHO_MIN, longitud_gancho
)


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
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "reset_txt":        0,
        "reset_dxf":        0,
        "elementos_manual": [],
        "editando_idx":     None,
        "frm_tipo":         "V",
        "frm_diam":         '3/8"',
        "frm_dim":          "3.00",
        "frm_dim_e":        "0.20x0.20",
        "frm_dim_malla":    "XX-050",
        "frm_gancho":       "",
        "frm_cant":         1,
        "frm_nombre":       "MANUAL",
        "frm_ubic":         "MANUAL",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN PÁGINA
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
    .resumen-manual {
        background: #c2185b;
        color: white;
        font-weight: bold;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 0.9rem;
        letter-spacing: 0.3px;
        word-break: break-all;
    }
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
    uploaded_txt = st.file_uploader("Archivo despiece vigas", type=["txt"],
                                    key=f"up_txt_{st.session_state['reset_txt']}")
    st.markdown("#### 📐 Columnas (.dxf)")
    uploaded_dxf = st.file_uploader("Archivo DXF columnas", type=["dxf","DXF"],
                                    key=f"up_dxf_{st.session_state['reset_dxf']}")
    st.markdown("---")
    n_manual = len(st.session_state["elementos_manual"])
    if n_manual:
        st.info(f"🔧 {n_manual} elemento(s) manual(es) agregado(s)")
    st.caption("v3.0 — NSR-10 Colombia")


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style='margin:0'>🏗️ Cuantificador de Acero — NSR-10</h2>
    <p style='margin:0; opacity:0.8; font-size:0.9rem'>
        Carga el .txt de vigas y/o el .dxf de columnas, o agrega elementos manualmente
    </p>
</div>
""", unsafe_allow_html=True)


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
#  HELPER: construir elemento a partir del formulario manual
# ─────────────────────────────────────────────────────────────────────────────
def _construir_elemento_manual(tipo, diametro, dim_str, gancho_key, cantidad,
                                gv_manual_override=None):
    datos_diam = BARRAS_NSR10.get(diametro, {})
    kg_m = datos_diam.get("kg_m", 0.0)

    if tipo == "V":
        try:
            longitud = float(dim_str.replace(",", "."))
        except:
            longitud = 1.0
        longitud = max(longitud, 0.01)

        gancho_info = GANCHOS_BARRA.get(gancho_key, GANCHOS_BARRA[""])
        ti = gancho_info["tipo_izq"]
        td = gancho_info["tipo_der"]
        gi = longitud_gancho(diametro, ti) if ti else 0.0
        gd = longitud_gancho(diametro, td) if td else 0.0
        lt = round(longitud + gi + gd, 4)
        pu = round(lt * kg_m, 3)
        return {
            "tipo":             "BARRA",
            "cantidad":         cantidad,
            "diametro":         diametro,
            "longitud":         longitud,
            "gancho_izq":       gi,
            "gancho_der":       gd,
            "tipo_gancho_izq":  ti,
            "tipo_gancho_der":  td,
            "longitud_total":   lt,
            "kg_m":             kg_m,
            "peso_unit":        pu,
            "peso_total":       round(pu * cantidad, 3),
            "manual":           True,
        }

    elif tipo == "E":
        try:
            partes = dim_str.lower().replace(",", ".").split("x")
            base   = float(partes[0])
            altura = float(partes[1]) if len(partes) > 1 else base
        except:
            base, altura = 0.20, 0.20
        base   = max(base, 0.01)
        altura = max(altura, 0.01)

        gv = gv_manual_override if gv_manual_override is not None else datos_diam.get("G135", GANCHO_MIN)
        gv = max(gv, GANCHO_MIN)
        lt = round(2 * (base + altura) + 2 * gv, 4)
        pu = round(lt * kg_m, 3)
        return {
            "tipo":           "ESTRIBO",
            "cantidad":       cantidad,
            "diametro":       diametro,
            "base":           base,
            "altura":         altura,
            "gancho_val":     gv,
            "num_ganchos":    2,
            "longitud_total": lt,
            "kg_m":           kg_m,
            "peso_unit":      pu,
            "peso_total":     round(pu * cantidad, 3),
            "manual":         True,
        }

    elif tipo == "M":
        datos_malla = MALLAS.get(dim_str, {})
        largo_std   = datos_malla.get("largo", 6.0)
        kg_ud       = datos_malla.get("kg_ud", 0.0)
        return {
            "tipo":           "MALLA",
            "cantidad":       cantidad,
            "diametro":       f"ø{datos_malla.get('diam_long', 0)}mm",
            "nombre_malla":   dim_str,
            "sep_lon":        datos_malla.get("sep_lon", 0.15),
            "sep_trans":      datos_malla.get("sep_trans", 0.15),
            "diam_long":      datos_malla.get("diam_long", 4),
            "diam_trans":     datos_malla.get("diam_trans", 4),
            "ancho_std":      datos_malla.get("ancho", 2.35),
            "largo_std":      largo_std,
            "longitud_total": largo_std,
            "kg_m":           0.0,
            "peso_unit":      kg_ud,
            "peso_total":     round(kg_ud * cantidad, 3),
            "manual":         True,
        }
    return None


def _resumen_fucsia(tipo, diametro, dim_str, gancho_key, cantidad):
    if tipo == "V":
        g_label = GANCHOS_BARRA.get(gancho_key, {}).get("label", "Sin gancho")
        return f"{cantidad}  V  {diametro}  {dim_str} m  ·  {g_label}"
    elif tipo == "E":
        return f"{cantidad}  E  {diametro}  {dim_str} m"
    elif tipo == "M":
        datos = MALLAS.get(dim_str, {})
        return f"{cantidad}  Malla  {dim_str}  {datos.get('ancho',2.35):.2f}×{datos.get('largo',6):.1f}m  {datos.get('kg_ud',0):.2f} kg/ud"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
#  MÓDULO DE INGRESO MANUAL
# ─────────────────────────────────────────────────────────────────────────────
def render_modulo_manual():
    st.markdown("## ➕ Agregar elementos manualmente")
    st.caption("Selecciona el tipo, diámetro, dimensión y gancho. Puedes editar los campos directamente antes de agregar.")

    idx_edit = st.session_state["editando_idx"]
    editando = idx_edit is not None and 0 <= idx_edit < len(st.session_state["elementos_manual"])

    if editando:
        st.info(f"✏️ Editando elemento #{idx_edit + 1}")

    # ── Fila de selectores ────────────────────────────────────────────────────
    col_tipo, col_diam, col_dim, col_gancho, col_cant = st.columns([1, 2, 2, 2, 1])

    with col_tipo:
        st.markdown("**Figura**")
        tipo_options = ["V — Barra", "E — Estribo", "M — Malla"]
        tipo_map     = {"V — Barra": "V", "E — Estribo": "E", "M — Malla": "M"}
        tipo_rev     = {v: k for k, v in tipo_map.items()}
        tipo_default_label = tipo_rev.get(st.session_state["frm_tipo"], "V — Barra")
        tipo_label = st.selectbox("Figura", tipo_options,
                                  index=tipo_options.index(tipo_default_label),
                                  label_visibility="collapsed", key="sel_tipo")
        tipo = tipo_map[tipo_label]
        st.session_state["frm_tipo"] = tipo

    with col_diam:
        st.markdown("**Diámetro**")
        if tipo == "M":
            diam_default = st.session_state.get("frm_dim_malla", LISTA_MALLAS[0])
            try:    diam_idx = LISTA_MALLAS.index(diam_default)
            except: diam_idx = 0
            diametro = st.selectbox("Malla", LISTA_MALLAS, index=diam_idx,
                                    label_visibility="collapsed", key="sel_diam_malla")
            st.session_state["frm_dim_malla"] = diametro
        else:
            diam_default = st.session_state.get("frm_diam", '3/8"')
            try:    diam_idx = LISTA_DIAMETROS.index(diam_default)
            except: diam_idx = 6
            diametro = st.selectbox("Diámetro", LISTA_DIAMETROS, index=diam_idx,
                                    label_visibility="collapsed", key="sel_diam")
            st.session_state["frm_diam"] = diametro

    with col_dim:
        st.markdown("**Dimensión**")
        if tipo == "V":
            dims_v = [f"{x/100:.2f}" for x in range(25, 1605, 25)]
            dim_default = st.session_state.get("frm_dim", "3.00")
            try:    dim_idx = dims_v.index(dim_default)
            except: dim_idx = dims_v.index("3.00") if "3.00" in dims_v else 0
            dim_sel = st.selectbox("Long. (m)", dims_v, index=dim_idx,
                                   label_visibility="collapsed", key="sel_dim_v")
            st.session_state["frm_dim"] = dim_sel
            dim_str = dim_sel
        elif tipo == "E":
            dim_default = st.session_state.get("frm_dim_e", "0.20x0.20")
            try:    dim_idx = DIMENSIONES_ESTRIBOS.index(dim_default)
            except: dim_idx = 0
            dim_sel = st.selectbox("Dim. estribo", DIMENSIONES_ESTRIBOS, index=dim_idx,
                                   label_visibility="collapsed", key="sel_dim_e")
            st.session_state["frm_dim_e"] = dim_sel
            dim_str = dim_sel
        else:
            dim_str = diametro
            datos_m = MALLAS.get(dim_str, {})
            st.info(f"{datos_m.get('ancho',2.35):.2f} × {datos_m.get('largo',6.0):.1f} m")

    with col_gancho:
        st.markdown("**Ganchos**")
        if tipo == "V":
            g_default = st.session_state.get("frm_gancho", "")
            try:    g_idx = list(GANCHOS_BARRA.keys()).index(g_default)
            except: g_idx = 5
            g_sel = st.selectbox("Gancho", list(GANCHOS_BARRA.keys()),
                                 format_func=lambda k: GANCHOS_BARRA[k]["label"],
                                 index=g_idx,
                                 label_visibility="collapsed", key="sel_gancho")
            st.session_state["frm_gancho"] = g_sel
            gancho_key = g_sel
        elif tipo == "E":
            datos_diam = BARRAS_NSR10.get(diametro, {})
            gv_default = max(datos_diam.get("G135", GANCHO_MIN), GANCHO_MIN)
            st.markdown(f"**G135°** = {gv_default:.3f} m")
            gancho_key = "G135"
        else:
            st.markdown("—")
            gancho_key = ""

    with col_cant:
        st.markdown("**Cant.**")
        cant = st.number_input("Cantidad", min_value=1, max_value=9999,
                               value=st.session_state.get("frm_cant", 1),
                               label_visibility="collapsed", key="num_cant")
        st.session_state["frm_cant"] = cant

    # ── Preview fucsia (siempre visible, basado en selectores principales) ──────
    st.markdown("---")
    resumen_txt = _resumen_fucsia(tipo, diametro, dim_str, gancho_key, cant)
    st.markdown(f'<div class="resumen-manual">BIEN &nbsp;|&nbsp; {resumen_txt}</div>',
                unsafe_allow_html=True)

    # Nombre y ubicación
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        nombre_elem = st.text_input("Nombre elemento (ej: VEP1-100)",
                                    value=st.session_state.get("frm_nombre","MANUAL"),
                                    key="ed_nombre")
        st.session_state["frm_nombre"] = nombre_elem
    with col_n2:
        ubic_elem = st.text_input("Ubicación (ej: PLACA1)",
                                  value=st.session_state.get("frm_ubic","MANUAL"),
                                  key="ed_ubic")
        st.session_state["frm_ubic"] = ubic_elem

    # ── Ajuste fino OPCIONAL (checkbox) ───────────────────────────────────────
    usar_ajuste = st.checkbox("✏️ Activar ajuste fino (edición manual de valores)",
                              value=False, key="chk_ajuste")

    dim_final    = dim_str
    gancho_final = gancho_key
    cant_final   = cant
    gv_ed        = None

    if usar_ajuste:
        col_e1, col_e2, col_e3 = st.columns([1, 2, 2])
        with col_e1:
            cant_final = st.number_input("Cant.", min_value=1, max_value=9999,
                                         value=int(cant), key="ed_cant")
        with col_e2:
            if tipo == "V":
                dim_final = st.text_input("Longitud (m)", value=dim_str, key="ed_dim_v",
                                          help="Longitud del cuerpo en metros. Ej: 3.70")
            elif tipo == "E":
                dim_final = st.text_input("Dimensión BxH (m)", value=dim_str, key="ed_dim_e",
                                          help="Formato: ancho x alto. Ej: 0.12x0.17")
            else:
                dim_final = dim_str
                st.text_input("Malla", value=dim_str, disabled=True, key="ed_dim_m")
        with col_e3:
            if tipo == "V":
                gancho_final = st.selectbox(
                    "Gancho", list(GANCHOS_BARRA.keys()),
                    format_func=lambda k: GANCHOS_BARRA[k]["label"],
                    index=list(GANCHOS_BARRA.keys()).index(gancho_key),
                    key="ed_gancho_v"
                )
            elif tipo == "E":
                datos_diam_ed = BARRAS_NSR10.get(diametro, {})
                gv_def = max(datos_diam_ed.get("G135", GANCHO_MIN), GANCHO_MIN)
                gv_ed = st.number_input(
                    f"Long. gancho G135° (m) — mín {GANCHO_MIN:.3f}",
                    min_value=GANCHO_MIN, max_value=1.0,
                    value=gv_def, step=0.005, format="%.3f",
                    key="ed_gv_e"
                )
                gancho_final = "G135"
            else:
                st.markdown("—")

    # ── Botones ────────────────────────────────────────────────────────────────
    st.markdown("---")
    btn_c1, btn_c2, btn_c3 = st.columns([2, 2, 1])

    with btn_c1:
        btn_label = "✅ Guardar cambios" if editando else "➕ ACEPTAR — Agregar elemento"
        if st.button(btn_label, type="primary", use_container_width=True, key="btn_aceptar"):

            elem_nuevo = _construir_elemento_manual(
                tipo, diametro, dim_final, gancho_final, cant_final,
                gv_manual_override=gv_ed if tipo == "E" else None
            )

            if elem_nuevo:
                contenedor = {
                    "item":          "M001",
                    "nombre":        nombre_elem.strip() or "MANUAL",
                    "ubicacion":     ubic_elem.strip() or "MANUAL",
                    "cantidad_vigas":1,
                    "barras":        [elem_nuevo],
                    "peso_total":    elem_nuevo["peso_total"],
                }
                if editando:
                    st.session_state["elementos_manual"][idx_edit] = contenedor
                    st.session_state["editando_idx"] = None
                    st.success("✅ Elemento actualizado correctamente")
                else:
                    st.session_state["elementos_manual"].append(contenedor)
                    st.success(f"✅ Elemento agregado — Total: {len(st.session_state['elementos_manual'])}")
                st.rerun()
            else:
                st.error("Error al construir el elemento. Verifica los datos.")

    with btn_c2:
        if editando:
            if st.button("❌ Cancelar edición", use_container_width=True, key="btn_cancelar"):
                st.session_state["editando_idx"] = None
                st.rerun()

    # ── Tabla de elementos manuales ────────────────────────────────────────────
    elems_manual = st.session_state["elementos_manual"]
    if elems_manual:
        st.markdown("### 📋 Elementos manuales agregados")

        rows = []
        for i, cont in enumerate(elems_manual):
            e = cont["barras"][0]
            if e["tipo"] == "MALLA":
                desc = f"Malla {e.get('nombre_malla','')}  {e.get('ancho_std',2.35):.2f}×{e.get('largo_std',6):.1f}m"
            elif e["tipo"] == "BARRA":
                gi_str = f"  gi={e['gancho_izq']:.3f}m" if e.get("gancho_izq") else ""
                gd_str = f"  gd={e['gancho_der']:.3f}m" if e.get("gancho_der") else ""
                desc = f"Barra {e['diametro']}  L={e['longitud']:.2f}m{gi_str}{gd_str}"
            else:
                desc = f"Estribo {e['diametro']}  {e.get('base',0):.2f}×{e.get('altura',0):.2f}m  G={e.get('gancho_val',0):.3f}m"

            rows.append({
                "#":           i + 1,
                "Nombre":      cont["nombre"],
                "Ubicación":   cont["ubicacion"],
                "Tipo":        e["tipo"],
                "Descripción": desc,
                "Cant.":       e["cantidad"],
                "L.Total(m)":  round(e["longitud_total"], 3),
                "P.Unit(kg)":  round(e["peso_unit"], 3),
                "P.Total(kg)": round(e["peso_total"], 3),
            })

        df_m = pd.DataFrame(rows)
        st.dataframe(df_m, use_container_width=True, hide_index=True,
                     column_config={
                         "P.Total(kg)": st.column_config.NumberColumn(format="%.3f"),
                         "P.Unit(kg)":  st.column_config.NumberColumn(format="%.3f"),
                         "L.Total(m)":  st.column_config.NumberColumn(format="%.3f"),
                     })

        peso_manual = sum(c["barras"][0]["peso_total"] for c in elems_manual)
        st.caption(f"{len(elems_manual)} elementos manuales — Peso total: {peso_manual:.3f} kg")

        # Botones por elemento
        st.markdown("**Gestionar elementos individuales:**")
        for i, cont in enumerate(elems_manual):
            col_info, col_edit, col_del = st.columns([4, 1, 1])
            e = cont["barras"][0]
            with col_info:
                st.markdown(f"**#{i+1}** — {cont['nombre']} / {cont['ubicacion']} | {e['tipo']} | {e['cantidad']} uds | {e['peso_total']:.3f} kg")
            with col_edit:
                if st.button("✏️ Editar", key=f"edit_{i}", use_container_width=True):
                    st.session_state["editando_idx"] = i
                    tipo_e = {"BARRA":"V","ESTRIBO":"E","MALLA":"M"}.get(e["tipo"],"V")
                    st.session_state["frm_tipo"]   = tipo_e
                    st.session_state["frm_diam"]   = e.get("diametro", '3/8"')
                    st.session_state["frm_nombre"] = cont["nombre"]
                    st.session_state["frm_ubic"]   = cont["ubicacion"]
                    st.session_state["frm_cant"]   = e["cantidad"]
                    if tipo_e == "V":
                        st.session_state["frm_dim"] = f"{e.get('longitud',1.0):.2f}"
                    elif tipo_e == "E":
                        st.session_state["frm_dim_e"] = f"{e.get('base',0.20):.2f}x{e.get('altura',0.20):.2f}"
                    elif tipo_e == "M":
                        st.session_state["frm_dim_malla"] = e.get("nombre_malla", LISTA_MALLAS[0])
                    st.rerun()
            with col_del:
                if st.button("🗑️ Eliminar", key=f"del_{i}", use_container_width=True):
                    st.session_state["elementos_manual"].pop(i)
                    if st.session_state.get("editando_idx") == i:
                        st.session_state["editando_idx"] = None
                    st.rerun()

        st.markdown("---")
        if st.button("🗑️ Limpiar TODOS los elementos manuales", use_container_width=True,
                     key="btn_limpiar"):
            st.session_state["elementos_manual"] = []
            st.session_state["editando_idx"] = None
            st.rerun()

        # PDF solo manuales
        st.markdown("---")
        st.subheader("📄 Generar PDF de elementos manuales")
        if st.button("🖨️ PDF — Solo elementos manuales", type="primary",
                     use_container_width=True, key="btn_pdf_manual_inline"):
            with st.spinner("Generando PDF…"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp_pdf = tmp.name
                generar_pdf(elems_manual, tmp_pdf, proyecto=f"{proyecto} — MANUAL")
                pdf_bytes = open(tmp_pdf,"rb").read()
                os.unlink(tmp_pdf)
            st.success("✅ PDF listo")
            st.download_button("⬇️ Descargar PDF manuales", pdf_bytes,
                file_name=f"Manual_{proyecto.replace(' ','_')}.pdf",
                mime="application/pdf", use_container_width=True,
                key="dl_pdf_manual_inline")


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
        filtro_ubic = cf1.multiselect("Ubicación", ubicaciones, default=ubicaciones,
                                      key=f"ubic_{etiqueta}")
        all_diams = sorted(set(e["diametro"] for v in elementos for e in v["barras"]))
        filtro_diam = cf2.multiselect("Diámetro", all_diams,
                                      default=all_diams, key=f"diam_{etiqueta}")

        rows = []; item = 1
        for vp in elementos:
            if vp["ubicacion"] not in filtro_ubic: continue
            for e in vp["barras"]:
                if e["diametro"] not in filtro_diam: continue
                if e["tipo"] == "BARRA":
                    desc = f"Barra {e['diametro']}  L={e['longitud']:.2f}m" \
                           + (f"  G.izq={e['gancho_izq']:.3f}" if e.get('gancho_izq') else "") \
                           + (f"  G.der={e['gancho_der']:.3f}" if e.get('gancho_der') else "")
                elif e["tipo"] == "ESTRIBO":
                    desc = f"Estribo {e['diametro']}  {e.get('base',0):.2f}x{e.get('altura',0):.2f}m"
                elif e["tipo"] == "MALLA":
                    desc = f"Malla {e.get('nombre_malla','')}  {e.get('ancho_std',2.35):.2f}x{e.get('largo_std',6):.1f}m"
                else:
                    desc = f"Gancho {e['diametro']}  L={e.get('base',0):.2f}m"

                manual_tag = " 🔧" if e.get("manual") else ""
                rows.append({
                    "Item": f"{item:04d}", etiqueta: vp["nombre"],
                    "Ubicación": vp["ubicacion"], "Tipo": e["tipo"] + manual_tag,
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

        st.markdown("---")
        st.subheader("📊 Resumen por diámetro")
        rd = defaultdict(float)
        for v in elementos:
            for e in v["barras"]: rd[e["diametro"]] += e["peso_total"]

        def _sort_key(x):
            s = x.replace("#","").replace("BAJA","0").replace("ø","").replace("mm","")
            try: return float(s.split(".")[0])
            except: return 99

        df_r = pd.DataFrame([
            {"Diámetro": k, "Peso (kg)": round(v,2), "Peso (ton)": round(v/1000,4)}
            for k,v in sorted(rd.items(), key=lambda x: _sort_key(x[0]))
        ])
        tot = df_r["Peso (kg)"].sum()
        df_r.loc[len(df_r)] = ["TOTAL", round(tot,2), round(tot/1000,4)]
        cr1,cr2 = st.columns([1,2])
        with cr1: st.dataframe(df_r, use_container_width=True, hide_index=True)
        with cr2:
            st.bar_chart(df_r[df_r["Diámetro"]!="TOTAL"].set_index("Diámetro")["Peso (kg)"],
                         use_container_width=True)

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

        st.markdown("---")
        reset_key = "reset_txt" if etiqueta == "Vigas" else "reset_dxf"
        if st.button(f"🗑️ Borrar {etiqueta}", use_container_width=True,
                     key=f"borrar_{etiqueta}"):
            st.session_state[reset_key] += 1
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TABS PRINCIPALES
# ─────────────────────────────────────────────────────────────────────────────
tab_labels = ["➕ Agregar Manual"]
if vigas_txt:    tab_labels.append("🧱 Vigas")
if columnas_dxf: tab_labels.append("🏛️ Columnas")
if vigas_txt and columnas_dxf: tab_labels.append("📊 Resumen General")

tabs = st.tabs(tab_labels)
idx  = 0

with tabs[idx]:
    render_modulo_manual()
idx += 1

if vigas_txt:
    vigas_con_manual = vigas_txt + st.session_state["elementos_manual"]
    render_seccion(vigas_con_manual, tabla_nsr, "Vigas", tabs[idx]); idx += 1

if columnas_dxf:
    render_seccion(columnas_dxf, tabla_nsr, "Columnas", tabs[idx]); idx += 1

# ── Tab Resumen General ──────────────────────────────────────────────────────
if vigas_txt and columnas_dxf:
    with tabs[idx]:
        st.subheader("📊 Resumen General del Proyecto")

        peso_vigas  = sum(v["peso_total"] for v in vigas_txt)
        peso_cols   = sum(v["peso_total"] for v in columnas_dxf)
        peso_manual = sum(c["barras"][0]["peso_total"] for c in st.session_state["elementos_manual"])
        peso_total  = peso_vigas + peso_cols + peso_manual

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Peso Vigas (kg)",    f"{peso_vigas:.2f}")
        c2.metric("Peso Columnas (kg)", f"{peso_cols:.2f}")
        c3.metric("Peso Total (kg)",    f"{peso_total:.2f}")
        c4.metric("Peso Total (ton)",   f"{peso_total/1000:.4f}")
        st.markdown("---")

        rd_v = defaultdict(float)
        rd_c = defaultdict(float)
        rd_l = defaultdict(float)
        rd_n = defaultdict(int)

        for v in vigas_txt + st.session_state["elementos_manual"]:
            for e in v["barras"]:
                rd_v[e["diametro"]] += e["peso_total"]
                rd_l[e["diametro"]] += e["longitud_total"] * e["cantidad"]
                rd_n[e["diametro"]] += e["cantidad"]
        for v in columnas_dxf:
            for e in v["barras"]:
                rd_c[e["diametro"]] += e["peso_total"]
                rd_l[e["diametro"]] += e["longitud_total"] * e["cantidad"]
                rd_n[e["diametro"]] += e["cantidad"]

        def _sk(x):
            s = x.replace("#","").replace("BAJA","0")
            try: return int(s)
            except: return 0

        diams = sorted(set(list(rd_v.keys()) + list(rd_c.keys())), key=_sk)
        rows_comb = []
        for d in diams:
            pt = rd_v[d] + rd_c[d]
            rows_comb.append({
                "Diámetro": d, "N° Barras": rd_n[d],
                "Long. Acum. (m)": round(rd_l[d], 2),
                "Vigas (kg)":     round(rd_v[d], 2),
                "Columnas (kg)":  round(rd_c[d], 2),
                "Total (kg)":     round(pt, 2),
                "Total (ton)":    round(pt/1000, 4),
            })

        df_comb = pd.DataFrame(rows_comb)
        total_row = {
            "Diámetro": "TOTAL",
            "N° Barras": df_comb["N° Barras"].sum(),
            "Long. Acum. (m)": round(df_comb["Long. Acum. (m)"].sum(), 2),
            "Vigas (kg)":    round(df_comb["Vigas (kg)"].sum(), 2),
            "Columnas (kg)": round(df_comb["Columnas (kg)"].sum(), 2),
            "Total (kg)":    round(df_comb["Total (kg)"].sum(), 2),
            "Total (ton)":   round(df_comb["Total (ton)"].sum(), 4),
        }
        df_comb = pd.concat([df_comb, pd.DataFrame([total_row])], ignore_index=True)
        st.dataframe(df_comb, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📈 Distribución de peso por diámetro")
        df_graf = df_comb[df_comb["Diámetro"] != "TOTAL"].set_index("Diámetro")[["Vigas (kg)", "Columnas (kg)"]]
        st.bar_chart(df_graf, use_container_width=True)

        st.markdown("---")
        st.subheader("📄 PDF Completo del Proyecto")
        gp1,gp2 = st.columns([2,1])
        with gp1:
            st.markdown("Incluye vigas (+ manuales), columnas y resumen ponderado final.")
        with gp2:
            if st.button("🖨️ PDF Proyecto Completo", type="primary",
                         use_container_width=True, key="btn_comb"):
                with st.spinner("Generando PDF completo…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp_pdf = tmp.name
                    todas_vigas = vigas_txt + st.session_state["elementos_manual"]
                    generar_pdf_combinado(todas_vigas, columnas_dxf, tmp_pdf, proyecto=proyecto)
                    pdf_bytes = open(tmp_pdf,"rb").read()
                    os.unlink(tmp_pdf)
                st.success("✅ PDF completo listo")
                st.download_button("⬇️ Descargar PDF Completo", pdf_bytes,
                    file_name=f"Proyecto_Completo_{proyecto.replace(' ','_')}.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_comb")
    idx += 1