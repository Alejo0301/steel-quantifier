"""
generador_pdf.py
----------------
Genera el PDF de cuantificación de acero a partir de la lista de vigas parseada.

Columnas del PDF:
  1. ITEM (001, 002, …)
  2. DIAGRAMA (imagen esquemática)
  3. CANT.
  4. DIÁMETRO
  5. LONGITUD (m)
  6. PESO UNIT. (kg)
  7. PESO TOTAL (kg)
  8. UBICACIÓN
"""

import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, HRFlowable, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.lib.colors import HexColor
import datetime

from diagramas import generar_diagrama


# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL_HEADER  = HexColor("#1a1a2e")
AZUL_SUB     = HexColor("#16213e")
AZUL_CLARO   = HexColor("#e8eaf6")
GRIS_FILA    = HexColor("#f5f5f5")
NARANJA      = HexColor("#e94560")
BLANCO       = colors.white


# ── Estilos ───────────────────────────────────────────────────────────────────
estilos = getSampleStyleSheet()

est_titulo = ParagraphStyle(
    "titulo",
    parent=estilos["Normal"],
    fontSize=14, fontName="Helvetica-Bold",
    textColor=BLANCO, alignment=TA_CENTER, spaceAfter=2
)
est_subtitulo = ParagraphStyle(
    "subtitulo",
    parent=estilos["Normal"],
    fontSize=9, fontName="Helvetica",
    textColor=AZUL_CLARO, alignment=TA_CENTER, spaceAfter=0
)
est_seccion = ParagraphStyle(
    "seccion",
    parent=estilos["Normal"],
    fontSize=10, fontName="Helvetica-Bold",
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


# ─────────────────────────────────────────────────────────────────────────────
#  ENCABEZADO DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
def _encabezado(proyecto="TRINIDAD CASA 2"):
    datos = [
        [
            Paragraph(f"CUANTIFICACIÓN DE ACERO — {proyecto}", est_titulo),
            Paragraph(
                f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}  |  NSR-10",
                est_subtitulo
            )
        ]
    ]
    t = Table(datos, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_HEADER),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [AZUL_HEADER]),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  FILA DE CABECERA DE SECCIÓN (nombre de la viga)
# ─────────────────────────────────────────────────────────────────────────────
def _cabecera_viga(viga, col_widths):
    texto = (f"  VIGA: {viga['nombre']}   |   UBICACIÓN: {viga['ubicacion']}"
             f"   |   CANTIDAD: {viga['cantidad_vigas']} ud."
             f"   |   PESO TOTAL VIGA: {viga['peso_total']:.2f} kg")
    fila = [[Paragraph(texto, est_seccion)]]
    total_w = sum(col_widths)
    t = Table(fila, colWidths=[total_w])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_SUB),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA DE ELEMENTOS DE UNA VIGA
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_elementos(viga, col_widths, item_global):
    HEADERS = ["ITEM", "DIAGRAMA", "CANT.", "DIÁMETRO",
               "LONG. TOTAL\n(m)", "PESO UNIT.\n(kg)", "PESO TOTAL\n(kg)", "UBICACIÓN"]

    filas = [HEADERS]
    row_heights = [22]

    for elem in viga["barras"]:
        item_str = f"{item_global[0]:04d}"
        item_global[0] += 1

        # Diagrama
        img_bytes = generar_diagrama(elem)
        if img_bytes:
            img = Image(io.BytesIO(img_bytes))
            # Escalar para que quepa en la celda
            max_w = col_widths[1] - 4 * mm
            max_h = 2.0 * cm
            ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
            img.drawWidth  = img.imageWidth  * ratio
            img.drawHeight = img.imageHeight * ratio
            diagrama_cell = img
        else:
            diagrama_cell = Paragraph("—", est_celda)

        if elem["tipo"] == "BARRA":
            desc_long = f"{elem['longitud_total']:.3f}"
            desc_ubicacion = viga["ubicacion"]
        else:
            if elem["tipo"] == "ESTRIBO":
                desc_long = f"{elem['longitud_total']:.3f}\n({elem['base']:.2f}×{elem['altura']:.2f})"
            else:
                desc_long = f"{elem['longitud_total']:.3f}"
            desc_ubicacion = viga["ubicacion"]

        fila = [
            Paragraph(item_str,                      est_celda_bold),
            diagrama_cell,
            Paragraph(str(elem["cantidad"]),         est_celda),
            Paragraph(elem["diametro"],              est_celda_bold),
            Paragraph(desc_long,                     est_celda),
            Paragraph(f"{elem['peso_unit']:.3f}",    est_celda),
            Paragraph(f"{elem['peso_total']:.3f}",   est_celda_bold),
            Paragraph(desc_ubicacion,                est_celda),
        ]
        filas.append(fila)
        row_heights.append(2.2 * cm)

    t = Table(filas, colWidths=col_widths, rowHeights=row_heights)

    style = TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_CLARO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 1), (-1, -1), "CENTER"),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.grey),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.0, AZUL_SUB),
        # Filas alternadas
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, GRIS_FILA]),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ])
    t.setStyle(style)
    return t


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_resumen(vigas, col_widths):
    """Tabla de resumen agrupada por diámetro."""
    from collections import defaultdict

    resumen = defaultdict(float)
    for viga in vigas:
        for elem in viga["barras"]:
            resumen[elem["diametro"]] += elem["peso_total"] * viga["cantidad_vigas"]

    total_w = sum(col_widths)
    filas = [[Paragraph("RESUMEN GENERAL POR DIÁMETRO", ParagraphStyle(
        "rs", parent=estilos["Normal"], fontSize=10,
        fontName="Helvetica-Bold", textColor=BLANCO, alignment=TA_CENTER))]]
    t_titulo = Table(filas, colWidths=[total_w])
    t_titulo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_HEADER),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    HEADERS_R = ["DIÁMETRO", "PESO TOTAL (kg)", "PESO TOTAL (ton)"]
    fila_h = [Paragraph(h, est_celda_bold) for h in HEADERS_R]
    filas_r = [fila_h]

    total_general = 0.0
    for diam in sorted(resumen.keys(), key=lambda x: int(x.replace("#", "").replace("BAJA", "0"))):
        peso = resumen[diam]
        total_general += peso
        filas_r.append([
            Paragraph(diam,                      est_celda_bold),
            Paragraph(f"{peso:.2f}",             est_celda),
            Paragraph(f"{peso/1000:.4f}",        est_celda),
        ])

    filas_r.append([
        Paragraph("TOTAL GENERAL", est_celda_bold),
        Paragraph(f"{total_general:.2f}", est_celda_bold),
        Paragraph(f"{total_general/1000:.4f}", est_celda_bold),
    ])

    cw_r = [total_w * 0.3, total_w * 0.35, total_w * 0.35]
    t_r = Table(filas_r, colWidths=cw_r)
    t_r.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  AZUL_CLARO),
        ("BACKGROUND",    (0, -1), (-1, -1), AZUL_CLARO),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0),  (-1, -1), 0.4, colors.grey),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0),  (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [BLANCO, GRIS_FILA]),
    ]))

    return [t_titulo, t_r]


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf(vigas, output_path, proyecto="TRINIDAD CASA 2"):
    """
    Genera el PDF de cuantificación.
    vigas: lista de dicts devuelta por parser.parsear_archivo
    output_path: ruta del archivo PDF de salida
    """
    page_w, page_h = landscape(A4)
    margin = 1.5 * cm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=f"Cuantificación Acero — {proyecto}",
        author="Cuantificador v1.0"
    )

    usable_w = page_w - 2 * margin

    # Anchos de columna: ITEM | DIAGRAMA | CANT | DIAM | LONG | PU | PT | UBIC
    col_widths = [
        usable_w * 0.055,   # ITEM
        usable_w * 0.22,    # DIAGRAMA
        usable_w * 0.055,   # CANT
        usable_w * 0.07,    # DIÁMETRO
        usable_w * 0.09,    # LONG
        usable_w * 0.09,    # PU
        usable_w * 0.09,    # PT
        usable_w * 0.13,    # UBICACIÓN
    ]

    story = []
    story.append(_encabezado(proyecto))
    story.append(Spacer(1, 0.4 * cm))

    item_global = [1]   # contador mutable

    # Agrupar por ubicación
    from collections import defaultdict
    grupos = defaultdict(list)
    for v in vigas:
        grupos[v["ubicacion"]].append(v)

    for ubicacion, grupo_vigas in grupos.items():
        # Título de grupo
        story.append(Spacer(1, 0.3 * cm))

        for viga in grupo_vigas:
            bloque = [
                _cabecera_viga(viga, col_widths),
                Spacer(1, 1 * mm),
                _tabla_elementos(viga, col_widths, item_global),
                Spacer(1, 0.3 * cm),
            ]
            story.append(KeepTogether(bloque))

    # Resumen final
    story.append(PageBreak())
    story.append(_encabezado(proyecto))
    story.append(Spacer(1, 0.5 * cm))
    for elem in _tabla_resumen(vigas, col_widths):
        story.append(elem)
        story.append(Spacer(1, 2 * mm))

    doc.build(story)
    print(f"✅ PDF generado: {output_path}")
