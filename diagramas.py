"""
diagramas.py
------------
Genera diagramas esquemáticos de barras y estribos usando matplotlib.
Devuelve imágenes en bytes (PNG) para incrustar en el PDF.
"""

import io
import math
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
def dibujar_barra(elem):
    L   = elem["longitud"]
    gi  = elem.get("gancho_izq", 0.0)
    gd  = elem.get("gancho_der", 0.0)
    ti  = elem.get("tipo_gancho_izq")
    td  = elem.get("tipo_gancho_der")

    total_w = L + gi + gd
    margin  = total_w * 0.10
    fig_w   = max(4.5, total_w * 0.65)
    fig_h   = 1.8

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-gi - margin, L + gd + margin)
    ax.set_ylim(-0.7, 0.7)
    ax.axis("off")

    y0 = 0.0

    ax.plot([0, L], [y0, y0], color=COLOR_BARRA, lw=LW, solid_capstyle="round")

    ax.annotate("", xy=(L, y0 + 0.38), xytext=(0, y0 + 0.38),
                arrowprops=dict(arrowstyle="<->", color=COLOR_TEXTO, lw=0.8))
    ax.text(L / 2, y0 + 0.50, f"{L:.2f} m", ha="center", va="bottom",
            fontsize=7, color=COLOR_TEXTO)

    if gi > 0 and ti:
        if ti == "L90":
            ax.plot([-gi, 0], [y0, y0], color=COLOR_GANCHO, lw=LW_GANCHO,
                    solid_capstyle="round")
            ax.plot([-gi, -gi], [y0, y0 - 0.32], color=COLOR_GANCHO,
                    lw=LW_GANCHO, solid_capstyle="round")
            ax.text(-gi / 2, y0 - 0.52, f"{gi:.2f} m", ha="center",
                    va="top", fontsize=6.5, color=COLOR_TEXTO)
        elif ti == "J180":
            theta = [math.pi / 2 + t * math.pi / 20 * i for i in range(21)]
            rx = [-gi / 2 + (gi / 2) * math.cos(t) for t in theta]
            ry = [y0 + (gi / 2) * math.sin(t) for t in theta]
            ax.plot(rx, ry, color=COLOR_GANCHO, lw=LW_GANCHO)

    if gd > 0 and td:
        if td == "L90":
            ax.plot([L, L + gd], [y0, y0], color=COLOR_GANCHO, lw=LW_GANCHO,
                    solid_capstyle="round")
            ax.plot([L + gd, L + gd], [y0, y0 - 0.32], color=COLOR_GANCHO,
                    lw=LW_GANCHO, solid_capstyle="round")
            ax.text(L + gd / 2, y0 - 0.52, f"{gd:.2f} m", ha="center",
                    va="top", fontsize=6.5, color=COLOR_TEXTO)

    ax.text(L / 2, y0 - 0.26, elem["diametro"], ha="center", va="top",
            fontsize=8, fontweight="bold", color=COLOR_BARRA)

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

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  GANCHO ABIERTO
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_gancho(elem):
    B  = elem["base"]
    gv = elem.get("gancho_val", 0.1)

    escala = 2.0 / max(B, 0.01)
    b  = B  * escala
    g  = gv * escala

    margin = 0.3
    fig_w  = max(2.0, b + margin * 2)
    fig_h  = 1.5

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin, b + margin)
    ax.set_ylim(-0.5, 0.8)
    ax.axis("off")

    y0 = 0.0
    ax.plot([0, b], [y0, y0], color=COLOR_BARRA, lw=LW, solid_capstyle="round")

    ax.plot([0, 0], [y0, y0 + g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")
    ax.plot([0, -g / math.sqrt(2)], [y0 + g, y0 + g + g / math.sqrt(2)],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    ax.plot([b, b], [y0, y0 + g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")
    ax.plot([b, b + g / math.sqrt(2)], [y0 + g, y0 + g + g / math.sqrt(2)],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    ax.text(b / 2, y0 - 0.3, elem["diametro"], ha="center", va="top",
            fontsize=8, fontweight="bold", color=COLOR_BARRA)

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
    elif t == "GANCHO":
        return dibujar_gancho(elem)
    return None