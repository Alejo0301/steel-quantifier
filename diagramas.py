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
from matplotlib.patches import FancyArrowPatch


# ── Colores y estilo ──────────────────────────────────────────────────────────
COLOR_BARRA   = "#1a1a2e"
COLOR_GANCHO  = "#16213e"
COLOR_TEXTO   = "#333333"
LW            = 2.5   # line width principal
LW_GANCHO     = 2.0


def _fig_a_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
#  BARRA LONGITUDINAL
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_barra(elem):
    """
    Dibuja una barra longitudinal con sus ganchos.
    elem dict con: longitud, gancho_izq, gancho_der, tipo_gancho_izq,
                   tipo_gancho_der, diametro
    """
    L   = elem["longitud"]
    gi  = elem.get("gancho_izq", 0.0)
    gd  = elem.get("gancho_der", 0.0)
    ti  = elem.get("tipo_gancho_izq")
    td  = elem.get("tipo_gancho_der")

    # Canvas: la barra ocupa el centro, ganchos a los lados
    total_w = L + gi + gd
    margin  = total_w * 0.08
    fig_w   = max(4.0, total_w * 0.6)
    fig_h   = 1.6

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-gi - margin, L + gd + margin)
    ax.set_ylim(-0.6, 0.6)
    ax.axis("off")

    y0 = 0.0   # línea central

    # ── Cuerpo de la barra ───────────────────────────────────────────────────
    ax.plot([0, L], [y0, y0], color=COLOR_BARRA, lw=LW, solid_capstyle="round")

    # Cota longitud recta
    ax.annotate("", xy=(L, y0 + 0.35), xytext=(0, y0 + 0.35),
                arrowprops=dict(arrowstyle="<->", color=COLOR_TEXTO, lw=0.8))
    ax.text(L / 2, y0 + 0.45, f"{L:.2f} m", ha="center", va="bottom",
            fontsize=7, color=COLOR_TEXTO)

    # ── Gancho IZQUIERDO ─────────────────────────────────────────────────────
    if gi > 0 and ti:
        if ti == "L90":
            # Gancho a 90° hacia abajo-izquierda
            ax.plot([-gi, 0], [y0, y0], color=COLOR_GANCHO, lw=LW_GANCHO,
                    solid_capstyle="round")
            ax.plot([-gi, -gi], [y0, y0 - 0.3], color=COLOR_GANCHO,
                    lw=LW_GANCHO, solid_capstyle="round")
            ax.text(-gi / 2, y0 - 0.50, f"{gi:.2f} m", ha="center",
                    va="top", fontsize=6.5, color=COLOR_TEXTO)
        elif ti == "J180":
            # Gancho semicircular a 180°
            theta = [math.pi / 2 + t * math.pi / 20 * i for i in range(21)]
            rx = [-gi / 2 + (gi / 2) * math.cos(t) for t in theta]
            ry = [y0 + (gi / 2) * math.sin(t) for t in theta]
            ax.plot(rx, ry, color=COLOR_GANCHO, lw=LW_GANCHO)

    # ── Gancho DERECHO ───────────────────────────────────────────────────────
    if gd > 0 and td:
        if td == "L90":
            ax.plot([L, L + gd], [y0, y0], color=COLOR_GANCHO, lw=LW_GANCHO,
                    solid_capstyle="round")
            ax.plot([L + gd, L + gd], [y0, y0 - 0.3], color=COLOR_GANCHO,
                    lw=LW_GANCHO, solid_capstyle="round")
            ax.text(L + gd / 2, y0 - 0.50, f"{gd:.2f} m", ha="center",
                    va="top", fontsize=6.5, color=COLOR_TEXTO)

    # Diámetro label
    ax.text(L / 2, y0 - 0.22, elem["diametro"], ha="center", va="top",
            fontsize=8, fontweight="bold", color=COLOR_BARRA)

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  ESTRIBO
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_estribo(elem):
    """
    Dibuja un estribo rectangular cerrado con gancho a 135°.
    elem dict con: base, altura, gancho_val, diametro
    """
    B  = elem["base"]
    H  = elem["altura"]
    gv = elem.get("gancho_val", 0.1)

    # Escalar para que quepa bien
    escala = 2.5 / max(B, H, 0.01)
    b = B * escala
    h = H * escala

    margin = 0.35
    fig_w  = max(2.5, b + 2 * margin)
    fig_h  = max(2.0, h + 2 * margin)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-margin, b + margin)
    ax.set_ylim(-margin, h + margin)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Rectángulo principal ─────────────────────────────────────────────────
    rect = plt.Polygon(
        [(0, 0), (b, 0), (b, h), (0, h)],
        closed=True, fill=False,
        edgecolor=COLOR_BARRA, linewidth=LW
    )
    ax.add_patch(rect)

    # ── Gancho a 135° en esquina superior derecha ────────────────────────────
    g = gv * escala
    # Dirección 135° desde (b, h): va hacia (-1, -1) normalizado
    dx = -g / math.sqrt(2)
    dy = -g / math.sqrt(2)
    ax.annotate("",
        xy=(b + dx, h + dy),
        xytext=(b, h),
        arrowprops=dict(arrowstyle="-", color=COLOR_GANCHO,
                        lw=LW_GANCHO, connectionstyle="arc3,rad=0"))
    ax.plot([b, b + dx], [h, h + dy], color=COLOR_GANCHO,
            lw=LW_GANCHO, solid_capstyle="round")

    # Segundo gancho simétrico en esquina superior izquierda (estribo cerrado)
    ax.plot([0, 0 - dx], [h, h + dy], color=COLOR_GANCHO,
            lw=LW_GANCHO, solid_capstyle="round")

    # ── Cotas ────────────────────────────────────────────────────────────────
    # Base
    ax.text(b / 2, -margin * 0.6, f"{B:.2f}", ha="center", va="top",
            fontsize=7, color=COLOR_TEXTO)
    # Altura
    ax.text(-margin * 0.6, h / 2, f"{H:.2f}", ha="right", va="center",
            fontsize=7, color=COLOR_TEXTO, rotation=90)
    # Diámetro
    ax.text(b / 2, h / 2, elem["diametro"], ha="center", va="center",
            fontsize=8, fontweight="bold", color=COLOR_BARRA, alpha=0.5)

    return _fig_a_bytes(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  GANCHO ABIERTO
# ─────────────────────────────────────────────────────────────────────────────
def dibujar_gancho(elem):
    """
    Dibuja un gancho abierto (tipo G).
    """
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

    # Gancho izquierdo
    ax.plot([0, 0], [y0, y0 + g], color=COLOR_GANCHO, lw=LW_GANCHO,
            solid_capstyle="round")
    ax.plot([0, -g / math.sqrt(2)], [y0 + g, y0 + g + g / math.sqrt(2)],
            color=COLOR_GANCHO, lw=LW_GANCHO, solid_capstyle="round")

    # Gancho derecho
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
    """Genera el diagrama correcto según el tipo de elemento."""
    t = elem.get("tipo", "")
    if t == "BARRA":
        return dibujar_barra(elem)
    elif t == "ESTRIBO":
        return dibujar_estribo(elem)
    elif t == "GANCHO":
        return dibujar_gancho(elem)
    return None
