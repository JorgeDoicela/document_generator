---
name: laboratorios-ia-ciberseguridad
description: Protocolo para resolución de prácticas, talleres y laboratorios técnicos de Inteligencia Artificial y Ciberseguridad. Estandariza la generación de evidencia real, código reproducible, demostraciones formales y experimentación verificable en capturas/.
---

# Laboratorios de Inteligencia Artificial y Ciberseguridad

Esta skill rige el desarrollo experimental, técnico y analítico de clases prácticas, laboratorios y talleres universitarios en la Facultad de Ingeniería (especialidad en Inteligencia Artificial y Ciberseguridad).

---

## 1. Principio Rector: Evidencia Real, Cero Simulación Ficticia

Queda estrictamente prohibido inventar o falsificar evidencia experimental:

1. **Evidencia Ejecutable en Repositorio:** Siempre que la práctica requiera código (algoritmos en Python, scripts en Bash, consultas de bases de datos, programas en Prolog), el código debe escribirse y ejecutarse directamente en el entorno (`.venv`) para capturar las salidas exactas de la consola o generar las gráficas reales.
   * Utilizar `bloques.codigo_bloque(doc, texto, etiqueta)` o `visual.bloque_codigo_word(doc, codigo, archivo=..., lenguaje=...)` para incrustar listados monoespaciados limpios, y el preset `tema="tecnico"` en `formato_institucional.nuevo_documento_tematico()` cuando no se exija un formato universitario específico.
2. **Evidencia de Entorno Físico, Pantallas o Insumos de Equipo:**
   * **Recorte Milimétrico de Evidencia:** Toda captura extraída de PDFs, documentos DOCX de compañeros o pantallas del sistema debe recortarse con coordenadas precisas, sin sangrado de ejercicios anteriores ni bordes cortados.
   * **Inserción Limpia:** Emplear `caja_captura_evidencia(doc, ruta_imagen, pie_de_figura)` para una presentación profesional centrada con pie explicativo en cursiva.
   * **Evaluación Crítica Obligatoria:** Toda evidencia de aportes preliminares de equipo o salidas de herramientas debe ir acompañada inmediatamente de su diagnóstico crítico (aciertos, fallos conceptuales subsanados y desarrollo formal riguroso).
3. **Ecuaciones y Fórmulas Formales:**
   * Generar en OMML vectorial nativo mediante `formula_bloque(doc, formula, etiqueta)`.
   * Segmentación automática de fórmulas de más de 75 caracteres mediante `dividir_formula_larga`.
4. **Prohibición de Cajas Coloreadas:**
   * Jamás usar cuadros o tablas celestes/sombreadas para consignas; usar `enunciado_formal(doc, texto, etiqueta, numero)`.

---

## 2. Estándares por Dominio Técnico

### Dominio 1: Representación del Conocimiento y Lógica Computacional
* **Lógica Proposicional:** Tablas de verdad exhaustivas ($2^n$ interpretaciones), análisis de satisfacibilidad, leyes de equivalencia y deducción formal.
* **Lógica de Primer Orden (FOL):** Formalización de enunciados con cuantificadores ($\forall, \exists$), sustituciones válidas, algoritmos de unificación y resolución por refutación (forma clausal, Skolemización).
* **Sistemas Basados en Reglas:** Bases de conocimiento estructuradas (hechos, reglas de inferencia, encadenamiento hacia adelante y hacia atrás).
* **Marcos (Frames) y Grafos de Conocimiento:** Modelado ontológico formal mediante `renderizar_diagrama_marco_formal` y `renderizar_diagrama_marcos_jerarquicos` de `plantillas/visual.py`. Prohibición de desbordamiento horizontal de texto sobre bordes perimetrales; estructura de dos niveles por ranura con facetas y tipos tipados.
* **Ontologías y Web Semántica (RDF / RDFS / OWL 2 / SPARQL):** Separación estricta entre TBox (clases, propiedades de objeto y axiomas en Lógica Descriptiva/FOL) y ABox (instancias y tripletas $\langle s, p, o \rangle$). Implementación reproducible con `rdflib` serializando a W3C Turtle (`.ttl`) y RDF/XML (`.rdf`), validación automatizada de axiomas mediante consultas SPARQL y grafos dirigidos sin cruce de aristas sobre nodos.

### Dominio 2: Ciberseguridad Defensiva y Redes
* **Modelado de Amenazas:** Aplicación de taxonomías estándar de la industria (MITRE ATT&CK, STRIDE, OWASP Top 10, NIST CSF).
* **Criptografía y Autenticación:** Análisis matemático de esquemas simétricos (AES), asimétricos (RSA, Diffie-Hellman), firmas digitales y algoritmos de resumen criptográfico (SHA-256, SHA-3).
* **Arquitectura de Redes:** Cálculos de direccionamiento IPv4 (VLSM) e IPv6, análisis de tablas de enrutamiento y políticas de control de acceso.

### Dominio 3: Inteligencia Artificial y Aprendizaje Automático
* **Búsqueda en Espacios de Estados:** Formalización de estado inicial, espacio de acciones, función de coste y heurísticas admisibles ($A^*$, Búsqueda Voraz).
* **Modelos Predictivos y Clasificación:** Formulación rigurosa de matrices de confusión, precisión, sensibilidad (*recall*), puntuación F1 y curvas ROC.
* **Funciones Matemáticas:** Ecuaciones vectoriales en OMML para funciones de activación (sigmoide, ReLU, softmax) y funciones de coste (Cross-Entropy, MSE).

---

## 3. Estructuración de Informes Técnicos de Práctica

Todo informe práctico debe estructurarse con rigor científico:

1. **Introducción y Objetivos:** Planteamiento conciso del marco conceptual y los objetivos de aprendizaje de la guía.
2. **Metodología y Configuración:** Parámetros del entorno de prueba (versiones de software, bibliotecas, hardware, topología).
3. **Desarrollo y Procedimiento:** Resolución metódica paso a paso con bloques de código comentados, tablas de datos y ecuaciones OMML.
4. **Análisis de Resultados:** Discusión analítica de los hallazgos observados, causas de errores o comparativas de rendimiento (no limitarse a pegar capturas sin interpretación).
5. **Conclusiones Técnicas:** Deducciones fundamentadas directamente en la experimentación realizada, alineadas con los objetivos planteados.
