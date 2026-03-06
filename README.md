# 🏗️ Cuantificador de Acero — NSR-10

Aplicación Streamlit para leer archivos `.txt` de despiece de vigas,
cuantificar el acero y generar un PDF profesional con diagramas.

---

## 📁 Estructura del proyecto

```
cuantificador_acero/
├── app.py              ← Interfaz Streamlit (ejecutar esto)
├── parser.py           ← Lee y parsea el archivo .txt
├── diagramas.py        ← Genera los diagramas de barras/estribos
├── generador_pdf.py    ← Produce el PDF final
├── requirements.txt    ← Dependencias Python
└── README.md
```

---

## ⚙️ Instalación

### 1. Requisitos previos
- Python 3.9 o superior
- pip actualizado

### 2. Crear entorno virtual (recomendado)
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## 🚀 Ejecutar la aplicación

```bash
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en `http://localhost:8501`

---

## 📋 Formato del archivo .txt esperado

### Encabezado NSR-10 (primeras líneas):
```
"#5"    1.552    .25    .25    .25
  ↑       ↑       ↑      ↑      ↑
Ref    kg/m   G90izq  G90der  G180
```

### Bloques de vigas:
```
"VEP1-100/PLACA1"     1
 1   "#5"  3.7   L.25   L.25     ← barra #5, 3.7m, gancho L ambos lados
 1   "#4"  1.5   L.2              ← barra #4, 1.5m, gancho L izquierdo
 2   "#5"  3.7   L.25   L.25
 26   E  "#3"  .12*.17   G.1     ← 26 estribos #3, 12×17cm, gancho 135°
```

### Reglas de ganchos:
- `L.25` = gancho a 90° de 0.25 m
- Primer gancho = **izquierdo**, segundo = **derecho**
- Sin gancho = barra recta
- `G.1` en estribos = gancho a 135° de 0.10 m

---

## 📄 PDF generado

El PDF incluye para cada viga:

| Col | Contenido |
|-----|-----------|
| 1 | Item (0001, 0002…) |
| 2 | Diagrama esquemático de la barra o estribo |
| 3 | Cantidad |
| 4 | Diámetro |
| 5 | Longitud total (m) |
| 6 | Peso unitario (kg) |
| 7 | Peso total (kg) |
| 8 | Ubicación |

Más una hoja final de **resumen por diámetro** con totales en kg y toneladas.

---

## 🔜 Próximas versiones
- [ ] Lectura de archivos CAD (.dxf) para columnas
- [ ] Exportación a Excel
- [ ] Agrupación y consolidación por diámetro para pedido a proveedor
- [ ] Validación cruzada CAD vs .txt
