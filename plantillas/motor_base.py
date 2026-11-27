# -*- coding: utf-8 -*-
"""Contrato base y utilidades compartidas para motores de maquetación documental.

Define el protocolo BaseDocumentEngine y centraliza las funciones de inyección
de marcadores XML de rúbrica (bookmarks) para trazabilidad en WordML.
"""
import itertools
import re
from typing import Any, List, Optional, Protocol, Union, runtime_checkable

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Constantes universales de marcado XML de rúbrica
PREFIJO_MARCA = "rubrica_"
SUFIJO_TRANSVERSAL = "_todo"

# Generador global continuo de IDs para marcadores de Word
_ids_marca = itertools.count(1)


def marcar_elemento(parrafo: Any, nombre: str) -> None:
    """Inserta un marcador invisible (w:bookmarkStart / w:bookmarkEnd) en el elemento WordML.

    Este marcador es detectado posteriormente por comprobar.py a nivel XML
    para vincular unívocamente la sección del documento con el criterio de evaluación.
    """
    ident = str(next(_ids_marca))
    inicio = OxmlElement("w:bookmarkStart")
    inicio.set(qn("w:id"), ident)
    inicio.set(qn("w:name"), nombre[:40])
    fin = OxmlElement("w:bookmarkEnd")
    fin.set(qn("w:id"), ident)
    parrafo._p.insert(1 if parrafo._p.pPr is not None else 0, inicio)
    parrafo._p.append(fin)


def normalizar_criterios(criterios: Optional[Union[str, List[str]]]) -> List[str]:
    """Limpia y valida una lista o cadena de identificadores de rúbrica (C1, C2...)."""
    if criterios is None:
        return []
    if isinstance(criterios, str):
        criterios = re.split(r"[,\s]+", criterios)
    ids = [c.strip().upper() for c in criterios if c and c.strip()]
    for c in ids:
        if not re.fullmatch(r"[A-Z0-9_]+", c):
            raise ValueError(f"ID de criterio no válido: {c!r} (usa formato C1, C2...)")
    return ids


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


# Registro extensible de motores documentales
_REGISTRO_MOTORES: dict[str, type] = {}


def registrar_motor(nombre: str, clase_motor: type) -> None:
    """Registra una implementación de motor documental en el catálogo central."""
    _REGISTRO_MOTORES[nombre.lower()] = clase_motor


def obtener_motor(nombre: str) -> Optional[type]:
    """Obtiene una clase de motor registrada por su identificador."""
    return _REGISTRO_MOTORES.get(nombre.lower())


def motores_disponibles() -> List[str]:
    """Lista todos los identificadores de motores registrados."""
    return sorted(_REGISTRO_MOTORES.keys())
