"""Banco común de fuentes bibliográficas académicas (APA 7).

Proporciona referencias canónicas pre-validadas para tareas de:
- Inteligencia Artificial y Razonamiento
- Ciberseguridad y Redes
- Comunicación y Habilidades Profesionales
- Lógica Formal y Metodología
"""

FUENTES_CARRERA = {
    # Inteligencia Artificial y Lógica
    "russell_norvig": {
        "autores": ["Russell, S.", "Norvig, P."],
        "anio": 2021,
        "titulo": "Artificial Intelligence: A Modern Approach (4.ª ed.)",
        "fuente": "Pearson",
    },
    "copi_cohen": {
        "autores": ["Copi, I. M.", "Cohen, C.", "Rodych, V."],
        "anio": 2018,
        "titulo": "Introduction to Logic (15.ª ed.)",
        "fuente": "Routledge",
        "url": "https://doi.org/10.4324/9781315144016",
    },
    "goodfellow_dl": {
        "autores": ["Goodfellow, I.", "Bengio, Y.", "Courville, A."],
        "anio": 2016,
        "titulo": "Deep Learning",
        "fuente": "MIT Press",
        "url": "https://www.deeplearningbook.org",
    },
    # Ciberseguridad y Normativas
    "nist_sp800_61": {
        "autores": ["National Institute of Standards and Technology"],
        "anio": 2012,
        "titulo": "Computer Security Incident Handling Guide",
        "detalles": "Special Publication 800-61 Rev. 2",
        "url": "https://doi.org/10.6028/NIST.SP.800-61r2",
    },
    "iso_27001": {
        "autores": ["International Organization for Standardization"],
        "anio": 2022,
        "titulo": "Information security, cybersecurity and privacy protection — Information security management systems — Requirements",
        "detalles": "ISO/IEC 27001:2022",
        "url": "https://www.iso.org/standard/27001",
    },
    "stallings_crypto": {
        "autores": ["Stallings, W."],
        "anio": 2022,
        "titulo": "Cryptography and Network Security: Principles and Practice (8.ª ed.)",
        "fuente": "Pearson",
    },
    "gdpr_eu": {
        "autores": ["Parlamento Europeo y Consejo de la Unión Europea"],
        "anio": 2016,
        "titulo": "Reglamento (UE) 2016/679 relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales (RGPD)",
        "fuente": "Diario Oficial de la Unión Europea",
        "detalles": "L 119",
        "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
    },
    # Comunicación Profesional y Metodología
    "fonseca_comunicacion": {
        "autores": ["Fonseca Yerena, M. S.", "Correa Pérez, A. W.", "Pineda Ramírez, M. I.", "Lemus Hernández, F. J."],
        "anio": 2016,
        "titulo": "Comunicación oral y escrita en el ámbito profesional (2.ª ed.)",
        "fuente": "Pearson Educación",
    },
}


def cargar_en_bibliografia(bib, *claves: str) -> list[str]:
    """Carga fuentes canónicas directamente en una instancia de apa_docx.Bibliografia.

    Devuelve la lista de claves efectivamente cargadas. Lanza KeyError si alguna
    clave solicitada no existe en FUENTES_CARRERA.
    """
    cargadas: list[str] = []
    for clave in claves:
        if clave not in FUENTES_CARRERA:
            disponibles = ", ".join(sorted(FUENTES_CARRERA))
            raise KeyError(f"Fuente común desconocida: {clave!r} (disponibles: {disponibles})")
        datos = FUENTES_CARRERA[clave]
        bib.agregar(
            clave,
            datos["autores"],
            datos["anio"],
            datos.get("titulo", ""),
            datos.get("fuente", ""),
            url=datos.get("url", ""),
            detalles=datos.get("detalles", ""),
            tipo=datos.get("tipo", "libro"),
        )
        cargadas.append(clave)
    return cargadas
