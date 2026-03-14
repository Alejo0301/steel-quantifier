"""
catalogos.py
------------
Tablas de referencia NSR-10: diámetros de barras y mallas electrosoldadas.
Datos de fábrica — no editables por el usuario.
"""

# ─────────────────────────────────────────────────────────────────────────────
#  TABLA DE BARRAS NSR-10
#  Campos: diam_mm, area_mm2, kg_m, L90, U180, G135, fy_mpa, l_max
# ─────────────────────────────────────────────────────────────────────────────
BARRAS_NSR10 = {
    '1-1/4"': {"diam_mm": 32.3,  "area_mm2": 819,  "kg_m": 6.404, "L90": 0.55, "U180": 0.42, "G135": 0.40, "fy": 420, "l_max": 14},
    '1"':     {"diam_mm": 25.4,  "area_mm2": 510,  "kg_m": 3.973, "L90": 0.40, "U180": 0.28, "G135": 0.26, "fy": 420, "l_max": 14},
    '7/8"':   {"diam_mm": 22.23, "area_mm2": 387,  "kg_m": 3.042, "L90": 0.35, "U180": 0.25, "G135": 0.23, "fy": 420, "l_max": 14},
    '3/4"':   {"diam_mm": 19.1,  "area_mm2": 284,  "kg_m": 2.235, "L90": 0.30, "U180": 0.21, "G135": 0.20, "fy": 420, "l_max": 14},
    '5/8"':   {"diam_mm": 15.9,  "area_mm2": 199,  "kg_m": 1.552, "L90": 0.25, "U180": 0.18, "G135": 0.15, "fy": 420, "l_max": 14},
    '1/2"':   {"diam_mm": 12.7,  "area_mm2": 129,  "kg_m": 0.994, "L90": 0.20, "U180": 0.15, "G135": 0.13, "fy": 420, "l_max": 14},
    '3/8"':   {"diam_mm": 9.5,   "area_mm2": 71,   "kg_m": 0.560, "L90": 0.15, "U180": 0.13, "G135": 0.10, "fy": 420, "l_max": 14},
    '1/4"':   {"diam_mm": 6.35,  "area_mm2": 31.7, "kg_m": 0.250, "L90": 0.10, "U180": 0.10, "G135": 0.09, "fy": 420, "l_max": 14},
    "D4.0":   {"diam_mm": 4.0,   "area_mm2": 12.6, "kg_m": 0.099, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D4.5":   {"diam_mm": 4.5,   "area_mm2": 15.9, "kg_m": 0.125, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D5.0":   {"diam_mm": 5.0,   "area_mm2": 0.154,"kg_m": 0.154, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D5.5":   {"diam_mm": 5.5,   "area_mm2": 23.8, "kg_m": 0.187, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D6.0":   {"diam_mm": 6.0,   "area_mm2": 28.3, "kg_m": 0.222, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D6.5":   {"diam_mm": 6.5,   "area_mm2": 33.2, "kg_m": 0.260, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D7.0":   {"diam_mm": 7.0,   "area_mm2": 38.5, "kg_m": 0.302, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D7.5":   {"diam_mm": 7.5,   "area_mm2": 44.2, "kg_m": 0.347, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D8.0":   {"diam_mm": 8.0,   "area_mm2": 50.2, "kg_m": 0.395, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
    "D8.5":   {"diam_mm": 8.5,   "area_mm2": 56.8, "kg_m": 0.446, "L90": 0.07, "U180": 0.07, "G135": 0.07, "fy": 420, "l_max": 6},
}

# Lista ordenada de diámetros para selectores
LISTA_DIAMETROS = list(BARRAS_NSR10.keys())

# Tipos de gancho para barras (V)
GANCHOS_BARRA = {
    "L":   {"label": "L  — Gancho 90° izquierdo",    "tipo_izq": "L90",  "tipo_der": None},
    "U":   {"label": "U  — Gancho 180° izquierdo",   "tipo_izq": "U180", "tipo_der": None},
    "G":   {"label": "G  — Gancho 135° izquierdo",   "tipo_izq": "G135", "tipo_der": None},
    "LL":  {"label": "L L — Gancho 90° ambos lados", "tipo_izq": "L90",  "tipo_der": "L90"},
    "UU":  {"label": "U U — Gancho 180° ambos lados","tipo_izq": "U180", "tipo_der": "U180"},
    "":    {"label": "(sin gancho)",                  "tipo_izq": None,   "tipo_der": None},
}

GANCHO_MIN = 0.075  # metros — mínimo absoluto NSR-10


def longitud_gancho(diametro: str, tipo: str) -> float:
    """Retorna la longitud de gancho según diámetro y tipo (L90, U180, G135)."""
    datos = BARRAS_NSR10.get(diametro, {})
    campo = {"L90": "L90", "U180": "U180", "G135": "G135"}.get(tipo, "L90")
    val = datos.get(campo, GANCHO_MIN)
    return max(val, GANCHO_MIN)


# ─────────────────────────────────────────────────────────────────────────────
#  GENERADOR DE LISTA DE DIMENSIONES DE ESTRIBOS
#  De 0.20x0.20 hasta 1.00x1.00 en incrementos de 0.05
#  Secuencia: 20x20, 20x25, 25x25, 25x30, 30x30, 30x35, ...
# ─────────────────────────────────────────────────────────────────────────────
def generar_dimensiones_estribos():
    """Genera lista de strings 'BxH' en metros para estribos."""
    dims = []
    bases = [i * 5 for i in range(4, 21)]  # 20 a 100 cm
    for b in bases:
        for h in bases:
            if h >= b:
                dims.append(f"{b/100:.2f}x{h/100:.2f}")
    return dims

DIMENSIONES_ESTRIBOS = generar_dimensiones_estribos()


# ─────────────────────────────────────────────────────────────────────────────
#  CATÁLOGO DE MALLAS ELECTROSOLDADAS
#  ancho_std=2.35m, largo_std=6m (estándar de fábrica)
#  Campos: diam_long_mm, sep_lon_m, diam_trans_mm, sep_trans_m,
#          ancho_std, largo_std, kg_unidad, fy
# ─────────────────────────────────────────────────────────────────────────────
MALLAS = {
    "XX-050": {"diam_long": 4,   "sep_lon": 0.25, "diam_trans": 4,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 11.50, "fy": 420},
    "XX-063": {"diam_long": 4,   "sep_lon": 0.20, "diam_trans": 4,   "sep_trans": 0.20, "ancho": 2.35, "largo": 6, "kg_ud": 14.10, "fy": 420},
    "XY-084": {"diam_long": 4,   "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 15.10, "fy": 420},
    "XX-084": {"diam_long": 4,   "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 18.80, "fy": 420},
    "M-086":  {"diam_long": 4,   "sep_lon": 0.10, "diam_trans": 4,   "sep_trans": 0.10, "ancho": 2.35, "largo": 6, "kg_ud": 27.621,"fy": 420},
    "XX-106": {"diam_long": 4.5, "sep_lon": 0.15, "diam_trans": 4.5, "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 23.80, "fy": 420},
    "XY-106": {"diam_long": 4.5, "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 17.60, "fy": 420},
    "XY-131": {"diam_long": 5,   "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.30, "ancho": 2.35, "largo": 6, "kg_ud": 20.40, "fy": 420},
    "L-098":  {"diam_long": 5,   "sep_lon": 0.20, "diam_trans": 5,   "sep_trans": 0.20, "ancho": 2.35, "largo": 6, "kg_ud": 21.95, "fy": 420},
    "XX-131": {"diam_long": 5,   "sep_lon": 0.15, "diam_trans": 5,   "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 29.30, "fy": 420},
    "XY-158": {"diam_long": 5.5, "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 23.50, "fy": 420},
    "XX-159": {"diam_long": 5.5, "sep_lon": 0.15, "diam_trans": 5.5, "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 35.50, "fy": 420},
    "XX-188": {"diam_long": 6,   "sep_lon": 0.15, "diam_trans": 6,   "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 42.20, "fy": 420},
    "XY-221": {"diam_long": 6.5, "sep_lon": 0.15, "diam_trans": 4,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 30.60, "fy": 420},
    "L-165":  {"diam_long": 6.5, "sep_lon": 0.20, "diam_trans": 6.5, "sep_trans": 0.20, "ancho": 2.35, "largo": 6, "kg_ud": 37.05, "fy": 420},
    "XX-221": {"diam_long": 6.5, "sep_lon": 0.15, "diam_trans": 6.5, "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 49.60, "fy": 420},
    "XY-257": {"diam_long": 7,   "sep_lon": 0.15, "diam_trans": 5,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 37.70, "fy": 420},
    "XX-257": {"diam_long": 7,   "sep_lon": 0.15, "diam_trans": 7,   "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 57.40, "fy": 420},
    "XX-295": {"diam_long": 7.5, "sep_lon": 0.15, "diam_trans": 7.5, "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 65.90, "fy": 420},
    "XY-335": {"diam_long": 8,   "sep_lon": 0.15, "diam_trans": 5,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 46.60, "fy": 420},
    "XX-335": {"diam_long": 8,   "sep_lon": 0.15, "diam_trans": 8,   "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 75.10, "fy": 420},
    "XY-378": {"diam_long": 8.5, "sep_lon": 0.15, "diam_trans": 5,   "sep_trans": 0.25, "ancho": 2.35, "largo": 6, "kg_ud": 84.70, "fy": 420},
    "XX-378": {"diam_long": 8.5, "sep_lon": 0.15, "diam_trans": 8.5, "sep_trans": 0.15, "ancho": 2.35, "largo": 6, "kg_ud": 51.50, "fy": 420},
}

LISTA_MALLAS = list(MALLAS.keys())