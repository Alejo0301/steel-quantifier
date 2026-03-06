"""
generador_pdf.py
----------------
Genera el PDF de cuantificación de acero.
Formato: Oficio (Legal) vertical
Cambios v2:
  - Tamaño oficio vertical (LETTER/Legal)
  - Diagramas más amplios
  - Pie de página con nombre del ingeniero
  - Agrupación de barras por longitud total por diámetro
  - Nuevo estilo visual limpio
"""

import io
from reportlab.lib.pagesizes import legal
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.colors import HexColor
import datetime
from collections import defaultdict

from diagramas import generar_diagrama


# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL_HEADER  = HexColor("#1a1a2e")
AZUL_SUB     = HexColor("#16213e")
AZUL_CLARO   = HexColor("#dde3f0")
GRIS_FILA    = HexColor("#f7f7f9")
ACENTO       = HexColor("#c0392b")
BLANCO       = colors.white
GRIS_BORDE   = HexColor("#cccccc")

INGENIERO    = "Ing. Alejandro Gutiérrez"

# Tamaño oficio vertical (Legal = 216 × 356 mm)
PAGE_SIZE = legal   # 8.5 × 14 pulgadas


# ── Estilos ───────────────────────────────────────────────────────────────────
estilos = getSampleStyleSheet()

est_titulo = ParagraphStyle(
    "titulo",
    parent=estilos["Normal"],
    fontSize=13, fontName="Helvetica-Bold",
    textColor=BLANCO, alignment=TA_LEFT, spaceAfter=0
)
est_subtitulo = ParagraphStyle(
    "subtitulo",
    parent=estilos["Normal"],
    fontSize=8, fontName="Helvetica",
    textColor=HexColor("#b0bcd0"), alignment=TA_RIGHT, spaceAfter=0
)
est_seccion = ParagraphStyle(
    "seccion",
    parent=estilos["Normal"],
    fontSize=9, fontName="Helvetica-Bold",
    textColor=BLANCO, alignment=TA_LEFT,
    leftIndent=4, spaceAfter=0
)
est_celda = ParagraphStyle(
    "celda",
    parent=estilos["Normal"],
    fontSize=7.5, fontName="Helvetica",
    alignment=TA_CENTER
)
est_celda_bold = ParagraphStyle(
    "celdabold",
    parent=estilos["Normal"],
    fontSize=7.5, fontName="Helvetica-Bold",
    alignment=TA_CENTER
)
est_pie = ParagraphStyle(
    "pie",
    parent=estilos["Normal"],
    fontSize=7, fontName="Helvetica",
    textColor=HexColor("#888888"), alignment=TA_CENTER
)


# ─────────────────────────────────────────────────────────────────────────────
#  PIE DE PÁGINA (canvas callback)
# ─────────────────────────────────────────────────────────────────────────────
def _pie_pagina(canvas, doc):
    canvas.saveState()
    w, h = PAGE_SIZE
    margin = 1.2 * cm
    y_pie = 0.7 * cm

    # Línea separadora
    canvas.setStrokeColor(GRIS_BORDE)
    canvas.setLineWidth(0.5)
    canvas.line(margin, y_pie + 5 * mm, w - margin, y_pie + 5 * mm)

    # Nombre ingeniero — izquierda
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(HexColor("#444444"))
    canvas.drawString(margin, y_pie, INGENIERO)

    # NSR-10 — centro
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#888888"))
    canvas.drawCentredString(w / 2, y_pie, "NSR-10 Colombia — Cuantificación de Acero")

    # Número de página — derecha
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - margin, y_pie, f"Página {doc.page}")

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────────────────────────────────────
def _encabezado(proyecto, col_total_w):
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    datos = [[
        Paragraph(f"CUANTIFICACIÓN DE ACERO  ·  {proyecto}", est_titulo),
        Paragraph(f"Generado: {fecha}  |  NSR-10", est_subtitulo)
    ]]
    t = Table(datos, colWidths=[col_total_w * 0.65, col_total_w * 0.35])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_HEADER),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  CABECERA DE VIGA
# ─────────────────────────────────────────────────────────────────────────────
def _cabecera_viga(viga, col_total_w):
    texto = (f"  VIGA: {viga['nombre']}   |   UBICACIÓN: {viga['ubicacion']}"
             f"   |   CANTIDAD: {viga['cantidad_vigas']} ud."
             f"   |   PESO TOTAL VIGA: {viga['peso_total']:.2f} kg")
    t = Table([[Paragraph(texto, est_seccion)]], colWidths=[col_total_w])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_SUB),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  RESUMEN POR DIÁMETRO AL FINAL DE CADA TABLA DE VIGA
# ─────────────────────────────────────────────────────────────────────────────
def _resumen_viga_por_diametro(viga, col_total_w):
    """Mini tabla de agrupación por diámetro debajo de la tabla de la viga."""
    from collections import defaultdict
    grupo_long = defaultdict(float)
    grupo_cant = defaultdict(int)
    for elem in viga["barras"]:
        diam = elem["diametro"]
        grupo_long[diam] += elem["longitud_total"] * elem["cantidad"]
        grupo_cant[diam] += elem["cantidad"]

    est_mini = ParagraphStyle("mini", parent=estilos["Normal"],
                              fontSize=7, fontName="Helvetica", alignment=TA_CENTER)
    est_mini_b = ParagraphStyle("minib", parent=estilos["Normal"],
                                fontSize=7, fontName="Helvetica-Bold", alignment=TA_CENTER)

    filas = [[
        Paragraph("AGRUPACIÓN POR DIÁMETRO", est_mini_b),
        Paragraph("N° BARRAS", est_mini_b),
        Paragraph("LONG. TOTAL ACUMULADA (m)", est_mini_b),
    ]]

    for diam in sorted(grupo_long.keys(),
                       key=lambda x: int(x.replace("#", "").replace("BAJA", "0"))):
        filas.append([
            Paragraph(diam, est_mini_b),
            Paragraph(str(grupo_cant[diam]), est_mini),
            Paragraph(f"{grupo_long[diam]:.2f} m", est_mini),
        ])

    cws = [col_total_w * 0.40, col_total_w * 0.25, col_total_w * 0.35]
    t = Table(filas, colWidths=cws)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HexColor("#eef0f8")),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.3, GRIS_BORDE),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, GRIS_FILA]),
        ("LINEABOVE",     (0, 0), (-1, 0), 1.0, AZUL_SUB),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA DE ELEMENTOS DE UNA VIGA
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_elementos(viga, col_widths, item_global):
    HEADERS = ["ITEM", "DIAGRAMA", "CANT.", "DIÁMETRO",
               "LONG. TOTAL\n(m)", "PESO UNIT.\n(kg)", "PESO TOTAL\n(kg)", "UBICACIÓN"]

    filas = [HEADERS]
    row_heights = [20]

    for elem in viga["barras"]:
        item_str = f"{item_global[0]:04d}"
        item_global[0] += 1

        img_bytes = generar_diagrama(elem)
        if img_bytes:
            img = Image(io.BytesIO(img_bytes))
            max_w = col_widths[1] - 3 * mm
            max_h = 2.6 * cm        # más alto para mejor visibilidad
            ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
            img.drawWidth  = img.imageWidth  * ratio
            img.drawHeight = img.imageHeight * ratio
            diagrama_cell = img
        else:
            diagrama_cell = Paragraph("—", est_celda)

        if elem["tipo"] == "BARRA":
            desc_long = f"{elem['longitud_total']:.3f}"
        elif elem["tipo"] == "ESTRIBO":
            desc_long = f"{elem['longitud_total']:.3f}\n({elem['base']:.2f}×{elem['altura']:.2f})"
        else:
            desc_long = f"{elem['longitud_total']:.3f}"

        fila = [
            Paragraph(item_str,                      est_celda_bold),
            diagrama_cell,
            Paragraph(str(elem["cantidad"]),         est_celda),
            Paragraph(elem["diametro"],              est_celda_bold),
            Paragraph(desc_long,                     est_celda),
            Paragraph(f"{elem['peso_unit']:.3f}",    est_celda),
            Paragraph(f"{elem['peso_total']:.3f}",   est_celda_bold),
            Paragraph(viga["ubicacion"],             est_celda),
        ]
        filas.append(fila)
        row_heights.append(2.7 * cm)

    t = Table(filas, colWidths=col_widths, rowHeights=row_heights)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_CLARO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 1), (-1, -1), "CENTER"),
        ("GRID",          (0, 0), (-1, -1), 0.3, GRIS_BORDE),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.2, AZUL_SUB),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, GRIS_FILA]),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  RESUMEN FINAL COMPLETO
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_resumen_final(vigas, col_total_w):
    """Resumen general agrupado por diámetro: peso + longitud acumulada."""
    resumen_peso = defaultdict(float)
    resumen_long = defaultdict(float)
    resumen_cant = defaultdict(int)

    for viga in vigas:
        nv = viga["cantidad_vigas"]
        for elem in viga["barras"]:
            diam = elem["diametro"]
            resumen_peso[diam] += elem["peso_total"] * nv
            resumen_long[diam] += elem["longitud_total"] * elem["cantidad"] * nv
            resumen_cant[diam] += elem["cantidad"] * nv

    # Título sección
    est_rs = ParagraphStyle("rs", parent=estilos["Normal"], fontSize=11,
                            fontName="Helvetica-Bold", textColor=BLANCO,
                            alignment=TA_CENTER)
    t_tit = Table([[Paragraph("RESUMEN GENERAL POR DIÁMETRO", est_rs)]],
                  colWidths=[col_total_w])
    t_tit.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_HEADER),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))

    HEADERS = ["DIÁMETRO", "N° BARRAS TOTAL",
               "LONG. ACUMULADA (m)", "PESO TOTAL (kg)", "PESO TOTAL (ton)"]
    filas = [[Paragraph(h, est_celda_bold) for h in HEADERS]]

    total_peso = 0.0
    total_long = 0.0
    total_cant = 0

    for diam in sorted(resumen_peso.keys(),
                       key=lambda x: int(x.replace("#", "").replace("BAJA", "0"))):
        peso = resumen_peso[diam]
        lon  = resumen_long[diam]
        cant = resumen_cant[diam]
        total_peso += peso
        total_long += lon
        total_cant += cant
        filas.append([
            Paragraph(diam,              est_celda_bold),
            Paragraph(str(cant),         est_celda),
            Paragraph(f"{lon:.2f}",      est_celda),
            Paragraph(f"{peso:.2f}",     est_celda),
            Paragraph(f"{peso/1000:.4f}", est_celda),
        ])

    # Fila TOTAL
    filas.append([
        Paragraph("TOTAL GENERAL",         est_celda_bold),
        Paragraph(str(total_cant),         est_celda_bold),
        Paragraph(f"{total_long:.2f}",     est_celda_bold),
        Paragraph(f"{total_peso:.2f}",     est_celda_bold),
        Paragraph(f"{total_peso/1000:.4f}", est_celda_bold),
    ])

    cws = [col_total_w * 0.16, col_total_w * 0.16,
           col_total_w * 0.22, col_total_w * 0.23, col_total_w * 0.23]
    t_r = Table(filas, colWidths=cws)
    t_r.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  AZUL_CLARO),
        ("BACKGROUND",    (0, -1), (-1, -1), HexColor("#dde3f0")),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0),  (-1, -1), 0.4, GRIS_BORDE),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [BLANCO, GRIS_FILA]),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.5, AZUL_HEADER),
    ]))

    return [t_tit, t_r]


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf(vigas, output_path, proyecto="TRINIDAD CASA 2"):
    page_w, page_h = PAGE_SIZE   # Legal vertical: 216 × 356 mm
    margin = 1.2 * cm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=1.5 * cm,
        title=f"Cuantificación Acero — {proyecto}",
        author=INGENIERO
    )

    usable_w = page_w - 2 * margin

    # Anchos de columna ajustados a oficio vertical
    # ITEM | DIAGRAMA | CANT | DIAM | LONG | PU | PT | UBIC
    col_widths = [
        usable_w * 0.06,    # ITEM
        usable_w * 0.30,    # DIAGRAMA
        usable_w * 0.06,    # CANT
        usable_w * 0.08,    # DIÁMETRO
        usable_w * 0.125,   # LONG
        usable_w * 0.125,   # PU
        usable_w * 0.125,   # PT
        usable_w * 0.125,   # UBICACIÓN
    ]

    story = []
    story.append(_encabezado(proyecto, usable_w))
    story.append(Spacer(1, 0.4 * cm))

    item_global = [1]

    grupos = defaultdict(list)
    for v in vigas:
        grupos[v["ubicacion"]].append(v)

    for ubicacion, grupo_vigas in grupos.items():
        story.append(Spacer(1, 0.3 * cm))

        for viga in grupo_vigas:
            bloque = [
                _cabecera_viga(viga, usable_w),
                Spacer(1, 1 * mm),
                _tabla_elementos(viga, col_widths, item_global),
                Spacer(1, 1 * mm),
                _resumen_viga_por_diametro(viga, usable_w),
                Spacer(1, 0.35 * cm),
            ]
            story.append(KeepTogether(bloque))

    # Página de resumen final
    story.append(PageBreak())
    story.append(_encabezado(proyecto, usable_w))
    story.append(Spacer(1, 0.6 * cm))
    for elem in _tabla_resumen_final(vigas, usable_w):
        story.append(elem)
        story.append(Spacer(1, 2 * mm))

    doc.build(story, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    print(f"✅ PDF generado: {output_path}")