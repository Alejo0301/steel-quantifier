"""
parser_dxf.py — Lee DXF de despiece de columnas → lista vigas[] para generador_pdf.py

Formatos T2 reconocidos:
  4#5L=7.40           → flexión: cantidad#diámetroL=longitud
  13#3C/8             → estribos zona (ignorado, se usa el texto de longitud)
  25#3(22x22)-115     → estribo cerrado: cant #diam (base x altura) - long_cm
  103#3(52x27)-185    → estribo cerrado rectangular
  206#3(28)-55        → estribo tipo C (rama): cant #diam (dim) - long_cm
  75#3-116cm          → formato viejo: cant #diam - long cm
  30x30 / 60x35       → sección columna
  PLACA1/CUBIERTA     → inicio sub-tramo
  Es 1 / Son 3        → cantidad de columnas idénticas en ese bloque
  .90 / 1.41          → traslapes (ignorados)
"""

import re
from collections import defaultdict

TABLA_NSR_DEFAULT = {
    "#2":{"kg_m":0.250}, "#3":{"kg_m":0.560}, "#3BAJA":{"kg_m":0.560},
    "#4":{"kg_m":0.994}, "#5":{"kg_m":1.552}, "#6":{"kg_m":2.235},
    "#7":{"kg_m":3.042}, "#8":{"kg_m":3.973}, "#9":{"kg_m":6.404},
    "#10":{"kg_m":7.500},
}

# ── Patrones ──────────────────────────────────────────────────────────────────
RE_FLEXION    = re.compile(r'^(\d+)#(\w+)L=([\d.]+)$',             re.IGNORECASE)
RE_ESTRIBO_C  = re.compile(r'^(\d+)#(\w+)C/([\d.]+)$',             re.IGNORECASE)
RE_EST_CUAD   = re.compile(r'^(\d+)#(\w+)\((\d+)x(\d+)\)-(\d+)$', re.IGNORECASE)  # 25#3(22x22)-115
RE_EST_RAMA   = re.compile(r'^(\d+)#(\w+)\((\d+)\)-(\d+)$',        re.IGNORECASE)  # 206#3(28)-55
RE_LONG_VIE   = re.compile(r'^(\d+)#(\w+)-([\d.]+)cm$',            re.IGNORECASE)  # 75#3-116cm
RE_SECCION    = re.compile(r'^(\d+)[xX](\d+)$')
RE_TRASLAPE   = re.compile(r'^[\d]+\.[\d]+$')   # decimales como 1.41, .90, 2.60
RE_NUM_SOLO   = re.compile(r'^\d+$')
RE_UBICACION  = re.compile(r'^(PLACA\d*|CUBIERTA|piso\w*|nivel\w*)$', re.IGNORECASE)
RE_ES_SON     = re.compile(r'^(Es|Son)\s+(\d+)$', re.IGNORECASE)


# ── Lectura cruda ──────────────────────────────────────────────────────────────
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


# ── Dividir cajón pequeño en sub-tramos por ubicación ─────────────────────────
def _dividir_subtramos(txts):
    ordenados = sorted(txts, key=lambda t: -t['y'])
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


# ── Separar T3 agrupados: "Columnas A-3, B-3, C-3" → ["Columna A-3","Columna B-3","Columna C-3"]
def _separar_nombres_t3(texto):
    partes = [p.strip() for p in texto.split(',')]
    nombres = []
    for p in partes:
        # Quitar prefijo existente (Columna/Columnas) y reconstruir limpio
        limpio = re.sub(r'(?i)^columnas?\s+', '', p).strip()
        nombres.append(f"Columna {limpio}")
    return nombres


# ── Construir barras ───────────────────────────────────────────────────────────
def _construir_barras(flexion, est_items, seccion, tabla_nsr, cant_cols):
    """
    flexion   : lista de {cantidad, diametro, longitud}
    est_items : lista de {tipo, cantidad, diametro, longitud_total, base, altura}
    cant_cols : multiplicador (Es 1 / Son 3)
    """
    barras = []

    for b in flexion:
        diam = b['diametro']
        kg_m = tabla_nsr.get(diam, {}).get('kg_m', 0.0)
        lt   = b['longitud']
        pu   = round(lt * kg_m, 3)
        pt   = round(pu * b['cantidad'], 3)
        barras.append({
            'tipo':'BARRA', 'cantidad':b['cantidad'], 'diametro':diam,
            'longitud':lt, 'gancho_izq':0.0, 'gancho_der':0.0,
            'tipo_gancho_izq':None, 'tipo_gancho_der':None,
            'longitud_total':lt, 'kg_m':kg_m, 'peso_unit':pu, 'peso_total':pt,
        })

    for e in est_items:
        diam = e['diametro']
        lt   = e['longitud_total']
        cant = e['cantidad']
        kg_m = tabla_nsr.get(diam, {}).get('kg_m', 0.0)
        pu   = round(lt * kg_m, 3)
        pt   = round(pu * cant, 3)
        base = e.get('base', 0.0)
        alt  = e.get('altura', 0.0)

        if e['tipo'] == 'ESTRIBO':
            barras.append({
                'tipo':'ESTRIBO', 'cantidad':cant, 'diametro':diam,
                'base':base, 'altura':alt, 'gancho_val':0.0,
                'longitud_total':lt, 'kg_m':kg_m, 'peso_unit':pu, 'peso_total':pt,
            })
        else:  # GANCHO tipo C
            barras.append({
                'tipo':'GANCHO', 'subtipo':'C', 'cantidad':cant, 'diametro':diam,
                'base':base, 'altura':0.0, 'gancho_val':0.0,
                'longitud_total':lt, 'kg_m':kg_m, 'peso_unit':pu, 'peso_total':pt,
            })

    return barras


# ── Parsear textos del cajón grande (sección, estribos, Es/Son) ────────────────
def _parsear_grande(txts_g):
    seccion     = ""
    cant_cols   = 1
    est_items   = []

    for t in txts_g:
        txt = t['text'].strip()

        # Es/Son → cantidad de columnas idénticas
        m = RE_ES_SON.match(txt)
        if m:
            cant_cols = int(m.group(2))
            continue

        # Sección columna
        m = RE_SECCION.match(txt)
        if m:
            seccion = txt
            continue

        # Estribo cerrado nuevo: 25#3(22x22)-115
        m = RE_EST_CUAD.match(txt)
        if m:
            cant = int(m.group(1)); diam = f"#{m.group(2)}"
            base = int(m.group(3)) / 100.0
            alt  = int(m.group(4)) / 100.0
            lt   = int(m.group(5)) / 100.0
            est_items.append({'tipo':'ESTRIBO','cantidad':cant,'diametro':diam,
                              'base':base,'altura':alt,'longitud_total':lt})
            continue

        # Estribo rama/C nuevo: 206#3(28)-55
        m = RE_EST_RAMA.match(txt)
        if m:
            cant = int(m.group(1)); diam = f"#{m.group(2)}"
            base = int(m.group(3)) / 100.0
            lt   = int(m.group(4)) / 100.0
            est_items.append({'tipo':'GANCHO','subtipo':'C','cantidad':cant,'diametro':diam,
                              'base':base,'altura':0.0,'longitud_total':lt})
            continue

        # Formato viejo: 75#3-116cm
        m = RE_LONG_VIE.match(txt)
        if m:
            cant = int(m.group(1)); diam = f"#{m.group(2)}"
            lt   = float(m.group(3)) / 100.0
            est_items.append({'tipo':'ESTRIBO','cantidad':cant,'diametro':diam,
                              'base':0.0,'altura':0.0,'longitud_total':lt})
            continue

    return seccion, cant_cols, est_items


# ── Parsear sub-tramo (cajón pequeño) ─────────────────────────────────────────
def _parsear_subtramo(txts_sub):
    flexion = []
    for t in txts_sub:
        txt = t['text'].strip()
        if RE_TRASLAPE.match(txt): continue
        if RE_NUM_SOLO.match(txt): continue
        if RE_ES_SON.match(txt):   continue
        m = RE_FLEXION.match(txt)
        if m:
            flexion.append({'cantidad':int(m.group(1)),
                            'diametro':f"#{m.group(2)}",
                            'longitud':float(m.group(3))})
    return flexion


# ── Función principal ──────────────────────────────────────────────────────────
def parsear_dxf(path, tabla_nsr=None):
    if tabla_nsr is None:
        tabla_nsr = TABLA_NSR_DEFAULT

    pairs   = _leer_pairs(path)
    c3_all  = _extraer_polylines(pairs, 'C3')
    textos  = _extraer_textos(pairs, {'T2','T3'})
    txts_t2 = [t for t in textos if t['layer']=='T2']
    txts_t3 = [t for t in textos if t['layer']=='T3']

    # Separar cajones grandes / pequeños por ancho
    anchos  = sorted(set(round(c['x_max']-c['x_min'],1) for c in c3_all))
    umbral  = (anchos[0]+anchos[-1])/2 if len(anchos)>=2 else anchos[0]
    grandes  = [c for c in c3_all if (c['x_max']-c['x_min']) >  umbral]
    pequenos = [c for c in c3_all if (c['x_max']-c['x_min']) <= umbral]

    def xk(c): return round(c['x_min'], 0)
    col_keys = sorted(set(xk(c) for c in grandes))

    vigas = []

    for ck in col_keys:
        col_grandes  = sorted([c for c in grandes  if xk(c)==ck], key=lambda c:-c['y_max'])
        col_pequenos = sorted([c for c in pequenos if xk(c)==ck], key=lambda c:-c['y_max'])

        # ── Nombre(s) T3 para cada cajón grande por proximidad Y ──────────
        def nombres_para_cajon(grande):
            if not txts_t3:
                return ["Columna"]
            x_centro = (grande['x_min'] + grande['x_max']) / 2
            candidatos = [t for t in txts_t3 if abs(t['x'] - x_centro) < 3.5]
            if not candidatos:
                candidatos = txts_t3
            t3 = min(candidatos, key=lambda t: abs(t['y'] - grande['y_max']))
            return _separar_nombres_t3(t3['text'])

        for grande in col_grandes:
            nombres   = nombres_para_cajon(grande)

            # Cajón pequeño del mismo tramo
            pequeno = next((p for p in col_pequenos
                            if p['y_min'] >= grande['y_min']-0.1
                            and p['y_max'] <= grande['y_max']+0.1), None)

            txts_g_all = [t for t in txts_t2 if _en_bbox(t, grande)]
            txts_p_all = [t for t in txts_t2 if pequeno and _en_bbox(t, pequeno)]
            txts_g_exc = [t for t in txts_g_all if t not in txts_p_all]

            # Del cajón grande: sección, cant_cols, estribos
            seccion, cant_cols, est_items = _parsear_grande(txts_g_exc)

            # Sub-tramos del cajón pequeño
            subtramos = _dividir_subtramos(txts_p_all) if txts_p_all else []
            if not subtramos:
                subtramos = [("TRAMO1", [])]

            # Ubicación para los estribos: primera ubicación real
            ubic_est = next((u for u,_ in subtramos if u and 'TRAMO' not in u), subtramos[0][0])

            # ── Estribos: UNA entrada por cajón grande × cant_cols ──────────
            if est_items:
                barras_est = _construir_barras([], est_items, seccion, tabla_nsr, cant_cols)
                if barras_est:
                    peso_est = round(sum(b['peso_total'] for b in barras_est), 3)
                    for nombre in nombres:
                        vigas.append({
                            'nombre': nombre, 'ubicacion': ubic_est,
                            'cantidad_vigas': cant_cols,
                            'seccion': seccion,
                            'barras': barras_est, 'peso_total': peso_est,
                        })

            # ── Flexión: una entrada por sub-tramo × nombre × cant_cols ────
            for ubic, txts_sub in subtramos:
                flexion = _parsear_subtramo(txts_sub)
                if not flexion: continue
                barras = _construir_barras(flexion, [], seccion, tabla_nsr, cant_cols)
                if not barras: continue
                peso = round(sum(b['peso_total'] for b in barras), 3)
                for nombre in nombres:
                    vigas.append({
                        'nombre': nombre, 'ubicacion': ubic or ubic_est,
                        'cantidad_vigas': cant_cols,
                        'seccion': seccion,
                        'barras': barras, 'peso_total': peso,
                    })

    return tabla_nsr, vigas


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/DESPIECES_COLUMNAS.DXF'
    tabla, vigas = parsear_dxf(path)

    nombres_unicos = sorted(set(v['nombre'] for v in vigas))
    peso_total     = sum(v['peso_total'] * v['cantidad_vigas'] for v in vigas)

    print(f"\n✅ {len(nombres_unicos)} columnas únicas — Peso total: {peso_total:.3f} kg\n")
    for nombre in nombres_unicos:
        mis_vigas = [v for v in vigas if v['nombre'] == nombre]
        peso_col  = sum(v['peso_total'] * v['cantidad_vigas'] for v in mis_vigas)
        cant      = mis_vigas[0]['cantidad_vigas']
        print(f"  {nombre} (x{cant}) — {peso_col:.2f} kg")
        for v in mis_vigas:
            for b in v['barras']:
                print(f"    {b['tipo']:8s} {b['diametro']:6s} x{b['cantidad']:3d}  L={b['longitud_total']:.3f}m  Pt={b['peso_total']:.3f}kg")