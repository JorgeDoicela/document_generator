# Arquitectura de Motores Documentales — `BaseDocumentEngine`

El sistema desacopla la lógica de maquetación estética (portadas, colores, tipografías y márgenes) del motor de auditoría estática XML mediante una interfaz base formal estandarizada en `plantillas/motor_base.py`.

---

## 1. Protocolo `BaseDocumentEngine`

Toda implementación de motor documental en `document_generator` implementa el protocolo formal `BaseDocumentEngine`:

```python
from typing import Any, List, Optional, Protocol, Union, runtime_checkable

@runtime_checkable
class BaseDocumentEngine(Protocol):
    """Protocolo formal para motores de maquetación documental."""

    def configurar_pagina(self, doc: Any, **kwargs: Any) -> Any:
        """Aplica márgenes, encabezados y pies de página."""
        ...

    def titulo_seccion(
        self,
        doc: Any,
        texto: str,
        nivel: int = 1,
        criterios: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> Any:
        """Inserta un encabezado estructurado con marcadores de rúbrica."""
        ...

    def marcar_transversal(self, doc: Any, *criterios: str) -> None:
        """Inyecta marcadores de criterios que aplican a todo el documento."""
        ...
```

---

## 2. Marcado XML Unificado de Rúbricas

Para que `comprobar.py` audite la correspondencia entre los criterios de evaluación y los contenidos del documento, `motor_base.py` centraliza la inyección de marcadores WordML:

```xml
<w:p>
  <w:bookmarkStart w:id="1" w:name="rubrica_C1"/>
  <w:r><w:t>1. Introducción y Marco Teórico</w:t></w:r>
  <w:bookmarkEnd w:id="1"/>
</w:p>
```

Para criterios de evaluación que evalúan la totalidad del documento (ortografía, normas APA, formato global), se añade el sufijo canónico `_todo`:
```xml
<w:p>
  <w:bookmarkStart w:id="2" w:name="rubrica_C2_todo"/>
  <w:bookmarkEnd w:id="2"/>
</w:p>
```

---

## 3. Catálogo y Registro Dinámico de Motores

El sistema dispone de un registro dinámico (`_REGISTRO_MOTORES`) que permite instanciar motores por identificador sin acoplar el código cliente a una implementación específica:

```python
from plantillas import motor_base

# Consulta de motores disponibles
print(motor_base.motores_disponibles())  # ['apa7', 'institucional']

# Instanciación por fábrica
ClaseMotor = motor_base.obtener_motor("institucional")
motor = ClaseMotor()
motor.configurar_pagina(doc)
```

### Motores Soportados:
1. **`apa7` ([MotorAPA7](01-motor-apa7.md)):** Maquetación estricta bajo American Psychological Association (APA) 7.ª edición para estudiantes (US Letter, Times New Roman 12 pt, interlineado doble, márgenes de 1", encabezados sin espaciado redundante, sangría francesa en referencias y numeración superior derecha en Times New Roman 12 pt).
2. **`institucional` ([MotorInstitucional](02-motor-institucional-y-temas.md)):** Maquetación configurable por temas JSON (`plantillas/temas.py` + `plantillas/formato_institucional.py`) para cualquier archivo `theme.json` en `themes/` o `themes/local/` (logos, paletas RGB, tipografía, encabezados y numeración dinámica).

---

## 4. Guía para Incorporar una Nueva Institución o Formato

En la mayoría de los casos no hace falta escribir Python: basta con extraer o crear un `theme.json` en `themes/local/<slug>/` con `./tareas temas --extraer plantilla.docx --nombre <slug>`.

Si se requiere lógica de maquetación personalizada para un formato nuevo (ej. `formato_revista`):

1. Crear `plantillas/formato_<nombre>.py`.
2. Implementar una clase que satisfaga `BaseDocumentEngine`.
3. Inyectar marcadores de rúbrica utilizando `marcar_elemento` y `normalizar_criterios` desde `plantillas.motor_base`.
4. Registrar el motor al final del archivo:
   ```python
   from .motor_base import registrar_motor
   registrar_motor("revista", MotorRevista)
   ```
5. Exportar el módulo en `plantillas/__init__.py`.
