"""
parser.py
---------
Lee y parsea el archivo .txt de despiece de vigas generado por el programa de figuración.
Retorna una lista de vigas con sus barras y estribos estructurados.
"""

import re


# ─────────────────────────────────────────────
#  TABLA NSR-10 (leída desde el encabezado del archivo)
# ─────────────────────────────────────────────
def parse_nsr_table(lines):
    """
    Lee las primeras líneas del archivo y construye la tabla de propiedades
    de barras según NSR-10.
    Formato esperado: "#5"    1.552    .25    .25    .25
    Retorna dict: { "#5": {"kg_m": 1.552, "g90_izq": 0.25, "g90_der": 0.25, "g180": 0.25} }
    """
    tabla = {}
    patron = re.compile(r'"(#\d+\w*)"[\s]+([\d.]+)[\s]+([\d.]+)[\s]+([\d.]+)[\s]+([\d.]+)')
    for linea in lines:
        m = patron.match(linea.strip())
        if m:
            ref = m.group(1)
            tabla[ref] = {
                "kg_m":    float(m.group(2)),
                "g90_izq": float(m.group(3)),
                "g90_der": float(m.group(4)),
                "g180":    float(m.group(5)),
            }
    return tabla


# ─────────────────────────────────────────────
#  PARSER DE VIGAS
# ─────────────────────────────────────────────
def parse_barra(tokens, tabla_nsr):
    """
    Parsea una línea de barra longitudinal.
    Formatos:
      cantidad  "#diametro"  longitud  [L.gancho_izq]  [L.gancho_der]
    Retorna dict con todos los campos calculados.
    """
    # tokens[0] = cantidad, tokens[1] = diametro, tokens[2] = longitud
    cantidad   = int(tokens[0])
    diametro   = tokens[1].strip('"')
    longitud   = float(tokens[2])

    # Ganchos
    gancho_izq = 0.0
    gancho_der = 0.0
    tipo_gancho_izq = None
    tipo_gancho_der = None

    for tok in tokens[3:]:
        tok = tok.strip()
        # Gancho tipo L (90°)
        m = re.match(r'L([\d.]+)', tok)
        if m:
            val = float(m.group(1))
            if gancho_izq == 0.0 and tipo_gancho_izq is None:
                gancho_izq = val
                tipo_gancho_izq = "L90"
            else:
                gancho_der = val
                tipo_gancho_der = "L90"
        # Gancho tipo J (180°) – por si aparece en el futuro
        m = re.match(r'J([\d.]+)', tok)
        if m:
            val = float(m.group(1))
            if gancho_izq == 0.0 and tipo_gancho_izq is None:
                gancho_izq = val
                tipo_gancho_izq = "J180"
            else:
                gancho_der = val
                tipo_gancho_der = "J180"

    longitud_total = longitud + gancho_izq + gancho_der

    kg_m = tabla_nsr.get(diametro, {}).get("kg_m", 0.0)
    peso_unit = round(longitud_total * kg_m, 3)
    peso_total = round(peso_unit * cantidad, 3)

    return {
        "tipo":          "BARRA",
        "cantidad":      cantidad,
        "diametro":      diametro,
        "longitud":      longitud,
        "gancho_izq":    gancho_izq,
        "gancho_der":    gancho_der,
        "tipo_gancho_izq": tipo_gancho_izq,
        "tipo_gancho_der": tipo_gancho_der,
        "longitud_total":longitud_total,
        "kg_m":          kg_m,
        "peso_unit":     peso_unit,
        "peso_total":    peso_total,
    }


def parse_estribo(tokens, tabla_nsr):
    """
    Parsea una línea de estribo o gancho.
    Formatos:
      cantidad  E  "#diametro"  base*altura  G.gancho
      cantidad  G  "#diametro"  dimension    G.gancho/gancho2
    """
    cantidad  = int(tokens[0])
    tipo_elem = tokens[1].strip().upper()   # "E" o "G"
    diametro  = tokens[2].strip('"')

    # Dimensión: puede ser "base*altura" o solo "dimension"
    dim_raw = tokens[3].strip()
    if '*' in dim_raw:
        partes = dim_raw.split('*')
        base   = float(partes[0])
        altura = float(partes[1])
    else:
        base   = float(dim_raw)
        altura = 0.0

    # Gancho del estribo: G.1  → 0.10 m final a 135°
    gancho_raw = tokens[4].strip() if len(tokens) > 4 else "G.1"
    # Puede venir como G.1/.1 (dos ganchos) o G.1
    gancho_val = 0.0
    num_ganchos = 1
    m = re.match(r'G([\d.]+)(?:/([\d.]+))?', gancho_raw)
    if m:
        gancho_val = float(m.group(1))
        if m.group(2):
            num_ganchos = 2   # gancho en los dos extremos del gancho abierto

    # Longitud del estribo cerrado: 2*(base+altura) + 2*gancho_135
    # Para gancho tipo G abierto: solo un lado más los ganchos
    kg_m = tabla_nsr.get(diametro, {}).get("kg_m", 0.0)

    if tipo_elem == "E":
        # Estribo cerrado
        longitud_total = round(2 * (base + altura) + 2 * gancho_val, 3)
    else:
        # Gancho abierto (G): longitud = dimensión + ganchos
        longitud_total = round(base + num_ganchos * gancho_val, 3)

    peso_unit  = round(longitud_total * kg_m, 3)
    peso_total = round(peso_unit * cantidad, 3)

    return {
        "tipo":          "ESTRIBO" if tipo_elem == "E" else "GANCHO",
        "cantidad":      cantidad,
        "diametro":      diametro,
        "base":          base,
        "altura":        altura,
        "gancho_val":    gancho_val,
        "num_ganchos":   num_ganchos,
        "longitud_total":longitud_total,
        "kg_m":          kg_m,
        "peso_unit":     peso_unit,
        "peso_total":    peso_total,
    }


def parse_vigas(lines, tabla_nsr):
    """
    Recorre el bloque de vigas y construye la lista de vigas.
    Retorna lista de dicts:
    {
      "nombre": "VEP1-100",
      "ubicacion": "PLACA1",
      "cantidad_vigas": 1,
      "barras": [...],
      "peso_total": float
    }
    """
    vigas = []
    viga_actual = None
    item_counter = 1

    patron_cabecera = re.compile(r'"([^"]+)"[\s]+(\d+)')

    for linea in lines:
        linea_strip = linea.strip()
        if not linea_strip or linea_strip.startswith("Libre") or linea_strip.startswith("LISTA"):
            continue

        # ¿Es cabecera de viga?
        m = patron_cabecera.match(linea_strip)
        if m and '/' in m.group(1):
            # Guardar viga anterior
            if viga_actual:
                _calcular_peso_viga(viga_actual)
                vigas.append(viga_actual)

            nombre_completo = m.group(1)   # ej: VEP1-100/PLACA1
            cant_vigas      = int(m.group(2))

            partes = nombre_completo.split('/')
            nombre    = partes[0]
            ubicacion = partes[1] if len(partes) > 1 else ""

            viga_actual = {
                "item":          f"{item_counter:03d}",
                "nombre":        nombre,
                "ubicacion":     ubicacion,
                "cantidad_vigas":cant_vigas,
                "barras":        [],
                "peso_total":    0.0,
            }
            item_counter += 1
            continue

        # ¿Es línea de barra o estribo dentro de una viga?
        if viga_actual:
            tokens = linea_strip.split()
            if len(tokens) < 3:
                continue
            # Detectar si es estribo/gancho: segundo token es E o G
            if tokens[1].upper() in ("E", "G"):
                try:
                    elem = parse_estribo(tokens, tabla_nsr)
                    viga_actual["barras"].append(elem)
                except Exception:
                    pass
            # Es barra longitudinal: segundo token empieza con "#"
            elif tokens[1].startswith('"#') or tokens[1].startswith('#'):
                try:
                    elem = parse_barra(tokens, tabla_nsr)
                    viga_actual["barras"].append(elem)
                except Exception:
                    pass

    # Última viga
    if viga_actual:
        _calcular_peso_viga(viga_actual)
        vigas.append(viga_actual)

    return vigas


def _calcular_peso_viga(viga):
    """Suma el peso total de todos los elementos de la viga (×cantidad de vigas)."""
    peso = sum(b["peso_total"] for b in viga["barras"])
    viga["peso_total"] = round(peso * viga["cantidad_vigas"], 3)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────
def parsear_archivo(filepath):
    """
    Lee el archivo .txt y retorna (tabla_nsr, lista_vigas).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    tabla_nsr  = parse_nsr_table(lines)
    lista_vigas = parse_vigas(lines, tabla_nsr)
    return tabla_nsr, lista_vigas


if __name__ == "__main__":
    import json, sys
    archivo = sys.argv[1] if len(sys.argv) > 1 else "LISTA_FIGURACION_MITAD_CONSTRUIR_VIGAS.txt"
    tabla, vigas = parsear_archivo(archivo)
    print("=== TABLA NSR-10 ===")
    print(json.dumps(tabla, indent=2))
    print(f"\n=== {len(vigas)} VIGAS PARSEADAS ===")
    for v in vigas:
        print(f"  {v['item']} | {v['nombre']:25s} | {v['ubicacion']:12s} | {len(v['barras'])} elementos | {v['peso_total']:.2f} kg")
