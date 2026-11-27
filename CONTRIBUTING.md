# Guía de Contribución

Gracias por tu interés en contribuir a **document_generator**. Este repositorio mantiene un estándar técnico sobrio, tipado y verificable mediante CI.

## Entorno de Desarrollo

```bash
# Linux / macOS
./setup.sh
.venv/bin/pip install -e ".[dev]"

# Windows (PowerShell)
.\setup.ps1
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Validaciones Obligatorias Antes de un Pull Request

```bash
ruff check plantillas tests
mypy plantillas
python -m unittest -v
```

## Convenciones

1. **Cero datos personales ni marcas propietarias:** nunca incluyas nombres reales, correos privados, logos con derechos de autor ni entregables personales en `materias/` o `tests/`.
2. **Desacoplamiento de motores:** cualquier formato documental nuevo debe implementarse como preset en `plantillas/temas.py` o como clase compatible con `BaseDocumentEngine` en `plantillas/motor_base.py`.
3. **Multiplataforma:** toda operación dependiente del SO (rutas, fuentes, subprocesos) debe encapsularse en `plantillas/plataforma.py`.
4. **Cobertura de pruebas:** todo módulo o bloque editorial nuevo debe incluir pruebas unitarias en `tests/`.
