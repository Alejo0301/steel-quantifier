"""
parser_dxf.py — Lee DXF de despiece de columnas → lista vigas[] para generador_pdf.py

Estructura DXF:
  C3 grande (ancho ~5.5) : cajón visual del tramo
  C3 pequeño (ancho ~3.0): cajón de etiquetas con sub-tramos separados por ubicación
  T2: etiquetas de hierro  |  T3: nombre de columna

Formatos T2:
  4#5L=7.40     → flexión: cantidad#diámetroL=longitud
  13#3C/8       → estribos zona: cantidad#diámetroC/espaciado
  75#3-116cm    → longitud estribo en cm
  30x30         → sección columna
  PLACA1/CUBIERTA → inicio de nuevo sub-tramo
  .90 / .10     → traslapes (ignorados)
  35 / 1 / 12   → conteos auxiliares (ignorados)
"""

import re
from collections import defaultdict

TABLA_NSR_DEFAULT = {
    "#2":{"kg_m":0.250}, "#3":{"kg_m":0.560}, "#3BAJA":{"kg_m":0.560},
    "#4":{"kg_m":0.994}, "#5":{"kg_m":1.552}, "#6":{"kg_m":2.235},
    "#7":{"kg_m":3.042}, "#8":{"kg_m":3.973}, "#9":{"kg_m":6.404},
    "#10":{"kg_m":7.500},
}

RE_FLEXION   = re.compile(r'^(\d+)#(\w+)L=([\d.]+)$',    re.IGNORECASE)
RE_ESTRIBO   = re.compile(r'^(\d+)#(\w+)C/([\d.]+)$',    re.IGNORECASE)
RE_LONG_EST  = re.compile(r'^(\d+)#(\w+)-([\d.]+)cm$',   re.IGNORECASE)
RE_SECCION   = re.compile(r'^(\d+)[xX](\d+)$')
RE_TRASLAPE  = re.compile(r'^\.\d+$')
RE_NUM_SOLO  = re.compile(r'^\d+$')
RE_UBICACION = re.compile(r'^(PLACA\d+|CUBIERTA|piso\w*|nivel\w*)$', re.IGNORECASE)


# ── Lectura cruda ──────────────────────────────────────────────────────────
def _leer_pairs(path):
    with open(path, 'r', encoding='latin-1') as f:
        raw = f.read()
    lines = raw.replace('\r\n','\n').replace('\r','\n').split('\n')
    pairs = []
    i = 0
    while i + 1 < len(lines):
        pairs.append((lines[i].strip(), lines[i+1].strip()))
        i += 2
    return pairs


def _extraer_polylines(pairs, layer):
    polys = []
    i = 0
    while i < len(pairs):
        code, val = pairs[i]
        if code == "0" and val == "POLYLINE":
            cur_layer = ""; verts = []
            j = i + 1
            while j < len(pairs):
                c, v = pairs[j]
                if c == "8": cur_layer = v
                if c == "0" and v == "VERTEX":
                    vx = vy = 0.0
                    k = j + 1
                    while k < len(pairs) and pairs[k][0] != "0":
                        if pairs[k][0] == "10": vx = float(pairs[k][1])
                        if pairs[k][0] == "20": vy = float(pairs[k][1])
                        k += 1
                    verts.append((vx, vy))
                if c == "0" and v == "SEQEND": break
                j += 1
            if cur_layer == layer and verts:
                xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
                polys.append({'x_min':min(xs),'x_max':max(xs),
                              'y_min':min(ys),'y_max':max(ys)})
        i += 1
    return polys


def _extraer_textos(pairs, layers):
    txts = []
    i = 0
    while i < len(pairs):
        code, val = pairs[i]
        if code == "0" and val == "TEXT":
            layer=""; text_val=""; x=y=0.0
            j = i + 1
            while j < len(pairs) and pairs[j][0] != "0":
                c, v = pairs[j]
                if c=="8": layer=v
                if c=="1": text_val=v
                if c=="10": x=float(v)
                if c=="20": y=float(v)
                j += 1
            if layer in layers and text_val.strip():
                txts.append({'layer':layer,'x':x,'y':y,'text':text_val.strip()})
        i += 1
    return txts


def _en_bbox(t, bbox, m=0.05):
    return (bbox['x_min']-m <= t['x'] <= bbox['x_max']+m and
            bbox['y_min']-m <= t['y'] <= bbox['y_max']+m)


# ── Dividir textos del cajón pequeño en sub-tramos por ubicación ───────────
def _dividir_subtramos(txts_pequeno):
    """
    Ordena los textos de arriba a abajo y los divide en grupos
    cada vez que aparece una etiqueta de ubicación (PLACA1, CUBIERTA…).
    Devuelve lista de (ubicacion, [textos]).
    """
    ordenados = sorted(txts_pequeno, key=lambda t: -t['y'])
    
    subtramos = []
    ubic_actual = None
    grupo = []

    for t in ordenados:
        txt = t['text'].strip()
        if RE_UBICACION.match(txt):
            if ubic_actual is not None or grupo:
                subtramos.append((ubic_actual or "TRAMO", grupo))
            ubic_actual = txt.upper()
            grupo = []
        else:
            grupo.append(t)

    if grupo or ubic_actual:
        subtramos.append((ubic_actual or "TRAMO", grupo))

    return subtramos


# ── Construir barras desde listas de flexion/estribos ─────────────────────
def _construir_barras(flexion, estribos, long_est, seccion, tabla_nsr, cant_est=None):
    barras = []

    for b in flexion:
        diam = b['diametro']
        kg_m = tabla_nsr.get(diam, {}).get('kg_m', 0.0)
        lt   = b['longitud']
        pu   = round(lt * kg_m, 3)
        pt   = round(pu * b['cantidad'], 3)
        barras.append({
            'tipo':'BARRA','cantidad':b['cantidad'],'diametro':diam,
            'longitud':lt,'gancho_izq':0.0,'gancho_der':0.0,
            'tipo_gancho_izq':None,'tipo_gancho_der':None,
            'longitud_total':lt,'kg_m':kg_m,'peso_unit':pu,'peso_total':pt,
        })

    # Usar cant_est del texto 75#3-116cm como fuente primaria de cantidad
    # Si no existe, sumar desde las líneas NNN#3C/8
    if cant_est:
        for diam, cant in cant_est.items():
            lt = long_est.get(diam, 0.0)
            if lt == 0.0: continue
            kg_m = tabla_nsr.get(diam, {}).get('kg_m', 0.0)
            pu   = round(lt * kg_m, 3)
            pt   = round(pu * cant, 3)
            base = alt = 0.0
            if seccion:
                try:
                    p = re.split(r'[xX]', seccion)
                    base = float(p[0]) / 100.0
                    alt  = float(p[1]) / 100.0
                except Exception: pass
            barras.append({
                'tipo':'ESTRIBO','cantidad':cant,'diametro':diam,
                'base':base,'altura':alt,'gancho_val':0.0,
                'longitud_total':lt,'kg_m':kg_m,'peso_unit':pu,'peso_total':pt,
            })
    else:
        est_diam = defaultdict(int)
        for e in estribos:
            est_diam[e['diametro']] += e['cantidad']
        for diam, cant in est_diam.items():
            lt = long_est.get(diam, 0.0)
            if lt == 0.0: continue
            kg_m = tabla_nsr.get(diam, {}).get('kg_m', 0.0)
            pu   = round(lt * kg_m, 3)
            pt   = round(pu * cant, 3)
            base = alt = 0.0
            if seccion:
                try:
                    p = re.split(r'[xX]', seccion)
                    base = float(p[0]) / 100.0
                    alt  = float(p[1]) / 100.0
                except Exception: pass
            barras.append({
                'tipo':'ESTRIBO','cantidad':cant,'diametro':diam,
                'base':base,'altura':alt,'gancho_val':0.0,
                'longitud_total':lt,'kg_m':kg_m,'peso_unit':pu,'peso_total':pt,
            })

    return barras


# ── Función principal ──────────────────────────────────────────────────────
def parsear_dxf(path, tabla_nsr=None):
    if tabla_nsr is None:
        tabla_nsr = TABLA_NSR_DEFAULT

    pairs   = _leer_pairs(path)
    c3_all  = _extraer_polylines(pairs, 'C3')
    textos  = _extraer_textos(pairs, {'T2','T3'})
    txts_t2 = [t for t in textos if t['layer']=='T2']
    txts_t3 = [t for t in textos if t['layer']=='T3']

    # Separar cajones grandes de pequeños por ancho
    anchos = sorted(set(round(c['x_max']-c['x_min'],1) for c in c3_all))
    umbral = (anchos[0]+anchos[-1])/2 if len(anchos)>=2 else anchos[0]
    grandes  = [c for c in c3_all if (c['x_max']-c['x_min']) >  umbral]
    pequenos = [c for c in c3_all if (c['x_max']-c['x_min']) <= umbral]

    # Agrupar por columna (franja X)
    def xk(c): return round(c['x_min'], 0)
    col_keys = sorted(set(xk(c) for c in grandes))

    vigas = []
    for ck in col_keys:
        col_grandes  = sorted([c for c in grandes  if xk(c)==ck], key=lambda c:-c['y_max'])
        col_pequenos = sorted([c for c in pequenos if xk(c)==ck], key=lambda c:-c['y_max'])

        # Nombre T3 más cercano
        x_centro = ck + (col_grandes[0]['x_max']-col_grandes[0]['x_min'])/2 if col_grandes else ck
        nombre = min(txts_t3, key=lambda t: abs(t['x']-x_centro))['text'] if txts_t3 else "Columna"

        for idx_g, grande in enumerate(col_grandes):
            # Cajón pequeño del mismo tramo
            pequeno = next((p for p in col_pequenos
                            if p['y_min'] >= grande['y_min']-0.1
                            and p['y_max'] <= grande['y_max']+0.1), None)

            # Textos del cajón grande (excluyendo los del pequeño)
            txts_g_all = [t for t in txts_t2 if _en_bbox(t, grande)]
            txts_p_all = [t for t in txts_t2 if pequeno and _en_bbox(t, pequeno)]
            txts_g_exc = [t for t in txts_g_all if t not in txts_p_all]

            # Del cajón grande: sección, longitud estribo, cantidad estribo, ubicación
            seccion_global = ""
            long_est_global = {}
            cant_est_global = {}
            ubic_grande = None
            for t in txts_g_exc:
                txt = t['text'].strip()
                if RE_UBICACION.match(txt): ubic_grande = txt.upper()
                m = RE_LONG_EST.match(txt)
                if m:
                    long_est_global[f"#{m.group(2)}"] = float(m.group(3))/100.0
                    cant_est_global[f"#{m.group(2)}"] = int(m.group(1))
                m = RE_SECCION.match(txt)
                if m: seccion_global = txt

            # ── Estribos: una sola entrada por cajón grande ──────────────
            if cant_est_global:
                barras_est = _construir_barras([], [], long_est_global,
                                               seccion_global, tabla_nsr, cant_est_global)
                if barras_est:
                    ubicacion_est = ubic_grande or f"TRAMO{idx_g+1}"
                    peso_est = round(sum(b['peso_total'] for b in barras_est), 3)
                    vigas.append({
                        'nombre': nombre, 'ubicacion': ubicacion_est,
                        'cantidad_vigas': 1, 'seccion': seccion_global,
                        'barras': barras_est, 'peso_total': peso_est,
                    })

            # ── Barras de flexión: una entrada por sub-tramo ──────────────
            subtramos = _dividir_subtramos(txts_p_all) if txts_p_all else []
            if not subtramos:
                subtramos = [(ubic_grande or f"TRAMO{idx_g+1}", [])]

            for ubic, txts_sub in subtramos:
                ubicacion = ubic or ubic_grande or f"TRAMO{idx_g+1}"
                flexion  = []
                seccion  = seccion_global

                for t in txts_sub:
                    txt = t['text'].strip()
                    if RE_TRASLAPE.match(txt): continue
                    if RE_NUM_SOLO.match(txt): continue
                    m = RE_FLEXION.match(txt)
                    if m:
                        flexion.append({'cantidad':int(m.group(1)),
                                        'diametro':f"#{m.group(2)}",
                                        'longitud':float(m.group(3))})
                        continue
                    m = RE_SECCION.match(txt)
                    if m:
                        seccion = txt
                        continue

                if not flexion: continue
                barras = _construir_barras(flexion, [], {}, seccion, tabla_nsr)
                if not barras: continue
                peso = round(sum(b['peso_total'] for b in barras), 3)
                vigas.append({
                    'nombre': nombre, 'ubicacion': ubicacion,
                    'cantidad_vigas': 1, 'seccion': seccion,
                    'barras': barras, 'peso_total': peso,
                })

    return tabla_nsr, vigas


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/DESPIECES_COLUMNAS.DXF'
    tabla, vigas = parsear_dxf(path)
    peso_total = sum(v['peso_total'] for v in vigas)
    print(f"\n✅ {len(vigas)} sub-tramos — Peso total: {peso_total:.3f} kg\n")
    for v in vigas:
        print(f"  {v['nombre']} / {v['ubicacion']} ({v['seccion']}) — {v['peso_total']:.2f} kg")
        for b in v['barras']:
            print(f"    {b['tipo']:8s} {b['diametro']:6s} x{b['cantidad']:3d}  L={b['longitud_total']:.3f}m  Pt={b['peso_total']:.3f}kg")
