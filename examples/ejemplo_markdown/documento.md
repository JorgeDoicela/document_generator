---
titulo: "Especificación Declarativa de Pipeline Documental"
subtitulo: "Ejemplo Reproducible Markdown/YAML — IEEE Numérico"
tema: apa7
estilo_citas: ieee
modalidad: individual
autor: "Ana Pérez"
institucion: "document_generator"
carrera: "Ingeniería de Software"
docente: "Comité Técnico"
fecha: "2026"
indice: false
resumen: "Este documento demuestra la compilación declarativa desde Markdown con frontmatter YAML hacia WordML (.docx), preservando marcadores de rúbrica, ecuaciones OMML, tablas estructuradas y citas numéricas IEEE."
palabras_clave:
  - Markdown
  - YAML
  - OMML
  - IEEE
referencias:
  - clave: russell2021
    autores: ["Russell, S.", "Norvig, P."]
    anio: 2021
    titulo: "Artificial Intelligence: A Modern Approach"
    fuente: "Pearson"
    detalles: "4.a ed."
    tipo: libro
  - clave: nist2024
    autores: ["National Institute of Standards and Technology"]
    anio: 2024
    titulo: "The NIST Cybersecurity Framework (CSF) 2.0"
    fuente: "U.S. Department of Commerce"
    url: "https://doi.org/10.6028/NIST.CSWP.29"
    tipo: informe
---

# 1. Fundamentos y Modelo Formal {#C1}

El enfoque declarativo separa el contenido técnico de la maquetación OpenXML. Según @russell2021, la formalización de reglas deterministas reduce la ambigüedad en sistemas automatizados, mientras que los marcos de gobernanza modernos exigen evidencia auditable [@nist2024].

> **Consigna:** Garantizar que el documento compilado cumpla el 100 % de los criterios de rúbrica sin fugas de sintaxis Markdown ni LaTeX crudo.

La condición de aprobación del documento se expresa formalmente mediante una ecuación vectorial OMML:

$$
\forall c \in \mathcal{R} : \text{Cobertura}(c) = 1 \land \text{Errores}(c) = 0 \implies \text{Aprobado}
$$ {leyenda="Ecuación 1. Condición formal de cobertura total de rúbrica."}

# 2. Comparativa Tabular y Código {#C2}

La tabla siguiente resume los estilos de citación soportados por el compilador declarativo:

| Estilo | Cita en Texto | Orden en Referencias | Uso Recomendado |
|---|---|---|---|
| `apa7` | `(Autor, 2024)` | Alfabético por apellido | Ensayos y trabajos académicos APA 7 |
| `ieee` | `[1]` | Orden de aparición | Artículos de ingeniería y RFCs |
| `vancouver` | `(1)` | Orden de aparición | Ciencias de la salud y reportes técnicos |

A continuación se muestra el comando mínimo para compilar este documento desde consola:

```bash
./tareas compilar examples/ejemplo_markdown/documento.md --sin-pdf
```

- Compila encabezados `#`, `##`, `###` con marcadores XML invisibles.
- Resuelve citas `[@clave]` y `@clave` según `estilo_citas`.
- Verifica automáticamente el `.docx` resultante cuando existe `TAREA.md`.

# Referencias {#C3}
