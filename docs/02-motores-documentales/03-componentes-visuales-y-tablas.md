# Componentes Visuales de Alta Fidelidad y Motor de Tablas Académicas

El módulo `plantillas/visual.py` proporciona componentes gráficos y tipográficos de alta fidelidad para la presentación de evidencias técnicas, ejecución de algoritmos y tablas comparativas en documentos WordML (DOCX) y PDF vectoriales.

---

## 1. Renderizado de Terminales CLI (`renderizar_terminal`)

Para evidenciar la ejecución de scripts, programas en C, entornos interactivos y pseudocódigo (ej. PSeInt CLI), el sistema implementa un motor de captura sintética a 300 DPI con super-sampling 2x y tarjeta estilo ventana de terminal moderna.

### Características Principales
* **Sanitización de Mojibake:** Erradica fallos históricos de codificación mixta (Latin-1/UTF-8) donde caracteres acentuados o especiales se corrompen en terminales de Linux (`AUTENTICACIÓN`, `contraseña`, `ÉXITO`).
* **Supresión de Secuencias ANSI:** Limpia secuencias de escape de control de cursor (`\x1b[?25h`, códigos de color VT100, posicionamiento de cursor).
* **Renderizado Dual Instantáneo:**
  * **Modo Oscuro (`Temas.DARK`):** Paleta Tokyo Night / Dark Slate, óptima para lectura digital y estética de laboratorio de ciberseguridad.
  * **Modo Claro (`Temas.LIGHT`):** Paleta Slate Academic Paper, óptima para impresión física, manuales técnicos y dossiers sin consumo excesivo de tinta.

### Uso Programático

```python
from plantillas.visual import Temas, renderizar_terminal

renderizar_terminal(
    titulo_ventana="PSeInt CLI — Ejercicio 1 (Autenticación)",
    comando_mostrado="./pseint ejercicio1.psc",
    salida_lineas=res.stdout,
    ruta_salida=Path("capturas/terminal_ej1.png"),
    tema=Temas.LIGHT,  # o Temas.DARK
    prompt_user="user@workstation:~$ ",
)
```

---

## 2. Bloques de Código Fuente en WordML (`bloque_codigo_word`)

Permite insertar fragmentos de código fuente estructurado en el lienzo de WordML con apariencia de editor moderno:
* Cabecera con icono, nombre del archivo y etiqueta de lenguaje (`keep_with_next = True`).
* Protección contra cortes de página entre cabecera y código mediante `w:cantSplit` en ambas filas.
* Columna de numeración de líneas alineada a la derecha con separador vertical.
* Respeto de fuentes monoespaciadas (`Consolas` / `Inconsolata`) con espaciado compacto (1.05 líneas).
* Paleta adaptativa en modos claro (`Temas.LIGHT`) y oscuro (`Temas.DARK`). Para inspeccionar visualmente todas las variantes de tablas, terminales y código en un único documento, ejecutar `./tareas estilos --catalogo`.

```python
from plantillas.visual import Temas, bloque_codigo_word

bloque_codigo_word(
    doc,
    codigo=codigo_fuente,
    archivo="ejercicio1_autenticacion.psc",
    lenguaje="PSeInt / Pseudocódigo",
    tema=Temas.LIGHT,
)
```

---

## 3. Motor de Tablas Académicas (`tabla_estilizada` y `EstilosTabla`)

El repositorio estandariza dos estilos oficiales y excluyentes para la generación de tablas, evitando redundancias y garantizando rigor académico:

```python
class EstilosTabla:
    APA = "apa"       # Opción 1: Norma Oficial APA 7.ª edición
    GRID = "grid"     # Opción 4: Cuadrícula Institucional Completa
```

### Comparativa de Estilos Autorizados

| Atributo de Diseño | Opción 1: Norma APA 7 (`EstilosTabla.APA`) | Opción 4: Cuadrícula Institucional (`EstilosTabla.GRID`) |
|---|---|---|
| **Líneas Verticales** | **Cero líneas verticales** (prohibidas por APA 7). | Bordes en todas las divisiones de columna (`#CCCCCC`). |
| **Líneas Horizontales** | **Exactamente 3 líneas**: superior e inferior de cabecera, e inferior de cierre. | Bordes entre todas las filas de datos. |
| **Fondo de Cabecera** | Blanco / transparente limpio (sin sombreado). | Gris institucional claro (`#E8E8E8`). |
| **Rótulo Superior** | `Tabla N` en negrita arriba, seguido del título en cursiva. | Texto de título integrado o rótulo formal. |
| **Notas de Tabla** | Al pie, iniciando con `Nota.` en cursiva. | Párrafo explicativo post-tabla. |
| **Contexto de Uso** | Journals científicos, tesis, papers y asignaturas con APA 7 estricto. | Prácticas de laboratorio de ingeniería y formatos institucionales/técnicos. |

### Integración en Motores de Documento y Anchos Fijos Proporcionales

Tanto `plantillas/apa_docx.py` como `plantillas/formato_institucional.py` (vía `plantillas/bloques.py`) delegan su renderizado al motor centralizado `tabla_estilizada()`:

* **Layout Fijo en OpenXML (`w:tblLayout="fixed"`):** Toda tabla establece explícitamente `w:tblLayout w:type="fixed"`, `w:tblW`, `w:tblGrid/w:gridCol` y `w:tcW` en twips (`dxa`) por celda, asegurando fidelidad estricta entre Microsoft Word y LibreOffice Writer.
* **Cálculo Proporcional Automático (`_calcular_anchos_proporcionales`):** Cuando no se suministran `anchos=[...]`, el motor calcula automáticamente el ancho de cada columna según la longitud media y el token indivisible más largo (ej. URIs RDF o identificadores), previniendo cortes de palabra en tablas densas.
* **Tipografía Configurable:** `tabla_academica()` / `inst.tabla()` exponen `anchos`, `tamano_cabecera` y `tamano_cuerpo` para tablas técnicas con columnas estrechas.

```python
# En formato_institucional.py / bloques.py (por defecto según el tema, con anchos fijos opcionales)
inst.tabla(doc, encabezados, filas, anchos=[2.02, 1.00, 1.98, 1.50], tamano_cuerpo=7.8)

# En apa_docx.py (por defecto APA, alternable a GRID o heredado del tema activo)
tabla(doc, None, "Descripción de la tabla", encabezados, filas, estilo=EstilosTabla.GRID)
```

### Configuración Global por Variable de Entorno

Sin modificar el código de los scripts de las materias, es posible forzar el estilo de todas las tablas mediante la variable de entorno:

```bash
# Forzar Opción 1 (Norma APA 7 oficial) en toda la ejecución
export ESTILO_TABLA=apa

# Forzar Opción 4 (Cuadrícula institucional) en toda la ejecución
export ESTILO_TABLA=grid
```

---

## 4. Estándar Editorial para Organizadores Gráficos y Diagramas

Los generadores de diagramas (mapas conceptuales, diagramas de flujo comunicativo, redes semánticas, esquemas de llaves y ruedas de atributos) siguen reglas visuales estrictas de publicación científica (IEEE/APA):

* **Fondo Blanco Limpio:** El lienzo se mantiene despejado sin gradientes ni sombras pesadas.
* **Cero Líneas Decorativas bajo Títulos:** Se prohíbe el uso de líneas rojas o divisorias decorativas llamativas bajo las cabeceras de los diagramas, permitiendo que la tipografía respire de forma natural sobre el lienzo.
* **Cero Barras Laterales de Acento ("Estética IA"):** Se prohíbe el uso de franjas o barras verticales coloreadas adheridas al borde izquierdo de tarjetas o nodos (`border-l-*`). Cada nodo emplea un contorno perimetral uniforme y fino (`2 px`), fondo blanco o tinte institucional tenue, jerarquía tipográfica y un separador horizontal discreto.
* **Resolución Vectorial y Alta Definición:** Exportación obligatoria a 300 DPI (`dpi=(300, 300)`).

### Primitivas Canónicas para Tarjetas Académicas (`dibujar_tarjeta_academica` y `envolver_texto_pil`)

El módulo `plantillas/visual.py` expone dos funciones reutilizables sobre Pillow para estandarizar todos los nodos de diagramas con ajuste exacto de texto en píxeles (cero colisión con bordes):

```python
from plantillas.visual import dibujar_tarjeta_academica

dibujar_tarjeta_academica(
    draw,
    caja=(x0, y0, x1, y1),
    titulo="TEXTO EXPOSITIVO",
    cuerpo="Palabra clave: Informar\nRegistro formal, definiciones y clasificación.",
    fuente_titulo=f_bold,
    fuente_cuerpo=f_reg,
    color_borde=(22, 101, 52),
    color_fondo=(240, 253, 244),
    color_titulo=(22, 101, 52),
    grosor_borde=2,
)
```

---

## 5. Nomenclatura Única Oficial de Entregables (`snake_case`)

Los archivos finales generados en `materias/` y copiados a `~/Descargas/` siguen estrictamente la convención oficial:
* **Entregas Individuales:** `nombre_apellido_<actividad>_<numero>.pdf` (ej. `ana_perez_tarea_practica_2.pdf`).
* **Entregas Grupales:** `grupo_<numero>_<actividad>_<numero>.pdf` (ej. `grupo_1_clase_practica_3.pdf`, `grupo_1_tarea_practica_3.pdf`).
* **Aislamiento en Descargas:** En `~/Descargas/` se copia **un único archivo PDF** por cada entrega final, sin alias duplicados ni archivos `.docx` temporales.
