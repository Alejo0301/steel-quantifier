"""
diagramas.py
------------
Genera diagramas esquemáticos de barras y estribos usando matplotlib.
Devuelve imágenes en bytes (PNG) para incrustar en el PDF.
"""

import io
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ── Colores y estilo ──────────────────────────────────────────────────────────
COLOR_BARRA   = "#1a1a2e"
COLOR_GANCHO  = "#c0392b"
COLOR_TEXTO   = "#444444"
LW            = 2.2
LW_GANCHO     = 2.0


def _fig_a_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
#  BARRA LONGITUDINAL
# ─────────────────────────────────────────────────────────────────────────────
def _dibujar_gancho_lado(ax, x, y0, g, tipo, lado="izq"):
    """
    Dibuja un gancho en el extremo de una barra.
    lado='izq' → el gancho sale hacia la izquierda (x=0)
    lado='der' → el gancho sale hacia la derecha (x=L)
    tipo: L90, U180, G135
    """
    signo = -1 if lado == "izq" else 1

    if tipo == "L90":
        # Extensión horizontal + vertical hacia abajo
        x_ext = x - signo * g
        ax.plot([x_ext, x], [y0, y0], color=COLOR_GANCHO, lw=LW_GANCHO,
                solid_capstyle="round")
        ax.plot([x_ext, x_ext], [y0, y0 - 0.32], color=COLOR_GANCHO,
                lw=LW_GANCHO, solid_capstyle="round")
        ax.text(x_ext + signo * g / 2, y0 - 0.52, f"{g:.2f}m",
                ha="center", va="top", fontsize=6.0, color=COLOR_TEXTO)

    elif tipo == "U180":
        # Semicírculo de diámetro g, regresa hacia el cuerpo
        r = g / 2
        cx = x - signo * r
        theta = np.linspace(0, math.pi, 40)
        rx = cx + r * np.cos(theta) * signo
        ry = y0 - r * np.sin(theta)
        ax.plot(rx, ry, color=COLOR_GANCHO, lw=LW_GANCHO)
        ax.text(cx, y0 - g - 0.12, f"{g:.2f}m",
                ha="center", va="top", fontsize=6.0, color=COLOR_TEXTO)

    elif tipo == "G135":
        # Diagonal 135° (hacia abajo-adentro)
        dx = signo * g / math.sqrt(2)
        dy = -g / math.sqrt(2)
        ax.plot([x, x - dx], [y0, y0 + dy], color=COLOR_GANCHO,
                lw=LW_GANCHO, solid_capstyle="round")
        ax.text(x - dx * 0.5, y0 + dy - 0.12, f"{g:.2f}m",
                ha="center", va="top", fontsize=6.0, color=COLOR_TEXTO)


def dibujar_barra(elem):
    L   = elem["longitud"]
    gi  = elem.get("gancho_izq", 0.0)
    gd  = elem.get("gancho_der", 0.0)
    ti  = elem.get("tipo_gancho_izq")
    td  = elem.get("tipo_gancho_der")

    extra_v = 0.55  # espacio vertical extra para ganchos U
    total_w = L + gi + gd
    margin  = max(total_w * 0.10, 0.15)
    fig_w   = max(4.5, total_w * 0.65)
    fig_h   = 2.2

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-gi - margin, L + gd + margin)
    ax.set_ylim(-extra_v - 0.2, 0.75)
    ax.axis("off")

    y0 = 0.0
    ax.plot([0, L], [y0, y0], color=COLOR_BARRA, lw=LW, solid_capstyle="round")

    # Cota de longitud del cuerpo
    ax.annotate("", xy=(L, y0 + 0.38), xytext=(0, y0 + 0.38),
                arrowprops=dict(arrowstyle="<->", color=COLOR_TEXTO, lw=0.8))
    ax.text(L / 2, y0 + 0.50, f"{L:.2f} m", ha="center", va="bottom",
            fontsize=7, color=COLOR_TEXTO)

    # Ganchos
    if gi > 0 and ti:
        _dibujar_gancho_lado(ax, 0, y0, gi, ti, lado="izq")
    if gd > 0 and td:
        _dibujar_gancho_lado(ax, L, y0, gd, td, lado="der")

    ax.text(L / 2, y0 - 0.15, elem["diametro"], ha="center", va="top",
            fontsize=8, fontweight="bold", color=COLOR_BARRA)

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  MALLA ELECTROSOLDADA
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_malla(elem):
    """
    Diagrama esquemático de malla electrosoldada.
    Cuadrícula 4 líneas longitudinales (verticales) × 4 transversales (horizontales).
    Proporcional a sep_lon vs sep_trans.
    """
    nombre     = elem.get("nombre_malla", "")
    sep_lon    = elem.get("sep_lon", 0.15)    # espaciado entre líneas verticales
    sep_trans  = elem.get("sep_trans", 0.15)  # espaciado entre líneas horizontales
    diam_long  = elem.get("diam_long", 4)
    diam_trans = elem.get("diam_trans", 4)
    ancho      = elem.get("ancho_std", 2.35)
    largo      = elem.get("largo_std", 6.0)

    N_lon   = 4   # líneas longitudinales (verticales)
    N_trans = 4   # líneas transversales (horizontales)

    # Proporciones visuales basadas en separaciones
    ratio = sep_lon / sep_trans if sep_trans > 0 else 1.0
    w_vis = 3.0
    h_vis = w_vis / ratio if ratio > 0 else 3.0
    h_vis = max(1.5, min(h_vis, 5.0))  # limitar altura visual

    margin = 0.5
    fig_w  = w_vis + 2 * margin
    fig_h  = h_vis + 2 * margin

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin, w_vis + margin)
    ax.set_ylim(-margin, h_vis + margin)
    ax.set_aspect("equal")
    ax.axis("off")

    # Líneas longitudinales (verticales — varillas en dirección del largo)
    xs_lon = [i * w_vis / (N_lon - 1) for i in range(N_lon)]
    for x in xs_lon:
        ax.plot([x, x], [0, h_vis], color=COLOR_BARRA, lw=1.8,
                solid_capstyle="round", alpha=0.85)

    # Líneas transversales (horizontales — varillas en dirección del ancho)
    ys_trans = [i * h_vis / (N_trans - 1) for i in range(N_trans)]
    for y in ys_trans:
        ax.plot([0, w_vis], [y, y], color=COLOR_GANCHO, lw=1.5,
                solid_capstyle="round", alpha=0.85)

    # Puntos de intersección (soldaduras)
    for x in xs_lon:
        for y in ys_trans:
            ax.plot(x, y, "o", color="#333333", markersize=3.5, zorder=5)

    # Cotas y etiquetas
    ax.text(w_vis / 2, -margin * 0.55,
            f"Sep.Long={sep_lon:.2f}m  (ø{diam_long}mm)",
            ha="center", va="top", fontsize=6.5, color=COLOR_BARRA)
    ax.text(-margin * 0.55, h_vis / 2,
            f"Sep.Trans={sep_trans:.2f}m\n(ø{diam_trans}mm)",
            ha="right", va="center", fontsize=6.0, color=COLOR_GANCHO,
            rotation=90, linespacing=1.3)
    ax.text(w_vis / 2, h_vis + margin * 0.35,
            f"{nombre}  |  {ancho:.2f}m × {largo:.1f}m",
            ha="center", va="bottom", fontsize=7, fontweight="bold",
            color=COLOR_BARRA)

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  ESTRIBO — ganchos a 135° según imagen de referencia
#  Dos ganchos paralelos diagonales en esquina superior derecha:
#  Gancho 1: desde la esquina (b, h) hacia abajo-izquierda
#  Gancho 2: desde un punto sobre la barra horizontal superior (desplazado a la izq)
#            también hacia abajo-izquierda, paralelo al primero
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_estribo(elem):
    B  = elem["base"]
    H  = elem["altura"]
    gv = elem.get("gancho_val", 0.10)

    escala = 2.8 / max(B, H, 0.01)
    b = B * escala
    h = H * escala
    g = gv * escala * 1.0   # longitud visual del gancho

    margin = 0.60
    fig_w  = max(3.2, b + 2 * margin)
    fig_h  = max(2.8, h + 2 * margin)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin, b + margin)
    ax.set_ylim(-margin, h + margin)
    ax.set_aspect("equal")
    ax.axis("off")

    # Rectángulo principal — en rojo igual que los ganchos
    rect = plt.Polygon(
        [(0, 0), (b, 0), (b, h), (0, h)],
        closed=True, fill=False,
        edgecolor=COLOR_GANCHO, linewidth=LW
    )
    ax.add_patch(rect)

    # Dirección diagonal 135° hacia adentro: abajo-izquierda
    dx = -g / math.sqrt(2)
    dy = -g / math.sqrt(2)

    # GANCHO 1: origen en (0.70*b, h) — barra horizontal superior, 30% desde esquina derecha
    x1 = 0.70 * b
    ax.plot([x1, x1 + dx], [h, h + dy],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    # GANCHO 2: origen en (b, 0.70*h) — barra vertical derecha, 30% desde esquina superior
    y2 = 0.70 * h
    ax.plot([b, b + dx], [y2, y2 + dy],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    # Cotas
    ax.text(b / 2, -margin * 0.55, f"{B:.2f}", ha="center", va="top",
            fontsize=7, color=COLOR_TEXTO)
    ax.text(-margin * 0.55, h / 2, f"{H:.2f}", ha="right", va="center",
            fontsize=7, color=COLOR_TEXTO, rotation=90)
    ax.text(b / 2, h / 2, elem["diametro"], ha="center", va="center",
            fontsize=8, fontweight="bold", color=COLOR_BARRA, alpha=0.5)

    # Nomenclatura del gancho: G.10, G.15, etc.
    gv_cm = int(round(gv * 100))
    label_g = f"G.{gv_cm:02d}" if gv_cm >= 10 else f"G.{gv_cm}"
    # Posición: junto al primer gancho (x1, h), desplazado arriba-izq
    ax.text(x1 - g * 0.15, h + g * 0.25, label_g,
            ha="right", va="bottom", fontsize=6.5,
            color=COLOR_GANCHO, fontweight="bold")

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  GANCHO TIPO C (estribo rama simple de columnas DXF)
#  Cuerpo vertical largo + arcos redondeados + patas cortas horizontales 90°
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_gancho_c(elem):
    dim  = elem.get("base", 0.28)    # dimensión del gancho (altura del cuerpo)
    lt   = elem.get("longitud_total", 0.55)
    diam = elem.get("diametro", "#3")

    # Proporciones fijas en coordenadas de figura
    alto   = 1.20          # altura visual del cuerpo vertical
    ancho  = alto * 0.22   # profundidad de la C (≈22% del alto)
    radio  = alto * 0.10   # radio de esquinas (≈10% del alto)
    doblez = alto * 0.18   # patas horizontales (≈18% del alto) — cortas

    margin_x = doblez + 0.25
    margin_y = radio  + 0.20
    fig_w = ancho + radio + margin_x + 0.55
    fig_h = alto  + radio * 2 + margin_y * 2

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin_x, ancho + radio + 0.55)
    ax.set_ylim(-margin_y, alto + radio * 2 + margin_y)
    ax.set_aspect("equal")
    ax.axis("off")

    x0 = 0.0   # x de la apertura izquierda
    y0 = 0.0   # y inferior de la apertura

    # Pata inferior (horizontal, hacia la izquierda)
    ax.plot([x0 - doblez, x0], [y0 - radio, y0 - radio],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    # Horizontal inferior
    ax.plot([x0, x0 + ancho], [y0 - radio, y0 - radio],
            color=COLOR_GANCHO, lw=LW_GANCHO)

    # Arco inferior (esquina inf-der)
    t_bot = np.linspace(-np.pi/2, 0, 40)
    ax.plot((x0 + ancho) + radio * np.cos(t_bot),
            y0            + radio * np.sin(t_bot),
            color=COLOR_GANCHO, lw=LW_GANCHO)

    # Cuerpo vertical derecho
    ax.plot([x0 + ancho + radio, x0 + ancho + radio],
            [y0, y0 + alto],
            color=COLOR_GANCHO, lw=LW_GANCHO)

    # Arco superior (esquina sup-der)
    t_top = np.linspace(0, np.pi/2, 40)
    ax.plot((x0 + ancho)  + radio * np.cos(t_top),
            (y0 + alto)   + radio * np.sin(t_top),
            color=COLOR_GANCHO, lw=LW_GANCHO)

    # Horizontal superior
    ax.plot([x0, x0 + ancho], [y0 + alto + radio, y0 + alto + radio],
            color=COLOR_GANCHO, lw=LW_GANCHO)

    # Pata superior (horizontal, hacia la izquierda)
    ax.plot([x0 - doblez, x0], [y0 + alto + radio, y0 + alto + radio],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    # Cota vertical (dimensión del gancho)
    xc  = x0 + ancho + radio + 0.12
    ym  = y0 + alto / 2
    dim_cm = int(round(dim * 100))
    ax.annotate("", xy=(xc, y0 + alto), xytext=(xc, y0),
                arrowprops=dict(arrowstyle="<->", color="#ffcc00", lw=0.9))
    ax.text(xc + 0.07, ym, f"{dim_cm}cm",
            ha="left", va="center", fontsize=6.5, color="#ffcc00")

    # Diámetro
    ax.text(xc + 0.07, y0 + alto + radio * 0.5, diam,
            ha="left", va="bottom", fontsize=7, fontweight="bold",
            color=COLOR_GANCHO)

    # Longitud total debajo
    ax.text(x0 + ancho / 2, y0 - radio - 0.12, f"L={lt:.3f}m",
            ha="center", va="top", fontsize=6.5, color="#888888")

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  GANCHO TIPO S (elemento G del txt)
#  Cuerpo horizontal + gancho izq sube y dobla derecha +
#                       gancho der baja y dobla izquierda
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_gancho(elem):
    B   = elem["base"]       # longitud del cuerpo
    gv  = elem.get("gancho_val", 0.1)

    escala = 2.5 / max(B, 0.01)
    b  = B  * escala
    g  = gv * escala * 1.2   # longitud visual del gancho

    margin = 0.4
    fig_w  = max(3.0, b + margin * 2)
    fig_h  = max(2.0, g * 2 + margin * 2)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin, b + margin)
    ax.set_ylim(-g - margin, g + margin)
    ax.set_aspect("equal")
    ax.axis("off")

    y0 = 0.0

    # Cuerpo horizontal
    ax.plot([0, b], [y0, y0], color=COLOR_BARRA, lw=LW, solid_capstyle="round")

    # Gancho IZQUIERDO: sube y dobla a la derecha (90°)
    ax.plot([0, 0], [y0, y0 + g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")
    ax.plot([0, g * 0.6], [y0 + g, y0 + g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")

    # Gancho DERECHO: baja y dobla a la izquierda (90°, opuesto)
    ax.plot([b, b], [y0, y0 - g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")
    ax.plot([b, b - g * 0.6], [y0 - g, y0 - g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")

    # Etiquetas ganchos
    gv_cm = int(round(gv * 100))
    g_label = f"G.{gv_cm:02d}" if gv_cm >= 10 else f"G.{gv_cm}"
    ax.text(-margin * 0.4, y0 + g * 0.5, g_label, ha="right", va="center",
            fontsize=6.5, color=COLOR_GANCHO, fontweight="bold")
    ax.text(b + margin * 0.4, y0 - g * 0.5, g_label, ha="left", va="center",
            fontsize=6.5, color=COLOR_GANCHO, fontweight="bold")

    # Diámetro y longitud cuerpo
    ax.text(b / 2, y0 + 0.15, elem["diametro"], ha="center", va="bottom",
            fontsize=8, fontweight="bold", color=COLOR_BARRA, alpha=0.7)
    ax.annotate("", xy=(b, y0 - g * 0.35), xytext=(0, y0 - g * 0.35),
                arrowprops=dict(arrowstyle="<->", color="#666666", lw=0.7))
    ax.text(b / 2, y0 - g * 0.55, f"{B:.2f} m", ha="center", va="top",
            fontsize=6.5, color="#666666")

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  DESPACHADOR
# ─────────────────────────────────────────────────────────────────────────────
def generar_diagrama(elem):
    t = elem.get("tipo", "")
    if t == "BARRA":
        return dibujar_barra(elem)
    elif t == "ESTRIBO":
        return dibujar_estribo(elem)
    elif t == "MALLA":
        return dibujar_malla(elem)
    elif t == "GANCHO":
        if elem.get("subtipo") == "C":
            return dibujar_gancho_c(elem)
        return dibujar_gancho(elem)
    return None