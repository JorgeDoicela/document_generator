# -*- coding: utf-8 -*-
"""Verificador real de citas y referencias bibliográficas (anti-alucinación).

Audita la existencia y veracidad real de las referencias bibliográficas extraídas
de un documento `.docx` o lista de entradas, detectando:
  - DOIs inexistentes (HTTP 404 en Crossref) o reciclados de otra obra distinta.
  - URLs rotas (HTTP 404/410) o dominios inexistentes.
  - Referencias sin DOI/URL contrastadas contra OpenAlex y OpenLibrary por título,
    autor y año de publicación.

Diseñado sin dependencias externas (solo biblioteca estándar) y con cliente HTTP
inyectable para pruebas unitarias deterministas sin acceso a red.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import comprobar as comp
    import rubrica as rub
else:
    from . import comprobar as comp
    from . import rubrica as rub

USER_AGENT = "document_generator/1.0 (Academic Citation Verifier; https://github.com/JorgeDoicela/document_generator)"
TIMEOUT_DEFECTO = 8.0

# Estados canónicos de verificación
ESTADO_VERIFICADA = "verificada"
ESTADO_AVISO = "aviso"
ESTADO_ERROR = "error"

_RE_DOI = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s,;<>\"']+)",
    re.IGNORECASE,
)
_RE_URL = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
_RE_ANIO = re.compile(r"\b((?:19|20)\d{2})\b")
_RE_PREFIJO_NUM = re.compile(r"^\s*(?:\[\d+\]|\d+\.)\s*")

_PALABRAS_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "under",
    "del", "las", "los", "una", "uno", "para", "con", "por", "sobre", "entre",
    "como", "hacia", "desde", "sus", "que", "edition", "edicion", "press",
    "editorial", "pearson", "springer", "elsevier", "wiley", "routledge",
}


@dataclass(frozen=True)
class RespuestaHTTP:
    """Respuesta simplificada de una petición HTTP para desacoplar red y tests."""

    status: int
    cuerpo: str = ""
    error: str = ""
    url_final: str = ""


FetcherFn = Callable[[str, str, float], RespuestaHTTP]


@dataclass
class ResultadoReferencia:
    """Resultado de verificación real para una entrada bibliográfica."""

    indice: int
    texto: str
    estado: str  # verificada | aviso | error
    codigo: str  # verificada_doi | doi_inexistente | doi_no_coincide | url_viva | url_rota | ...
    detalle: str
    doi: Optional[str] = None
    url: Optional[str] = None
    fuente_verificacion: str = ""


@dataclass
class InformeVerificacionCitas:
    """Resultado agregado de la verificación real de todas las referencias."""

    resultados: List[ResultadoReferencia] = field(default_factory=list)

    @property
    def verificadas(self) -> List[ResultadoReferencia]:
        return [r for r in self.resultados if r.estado == ESTADO_VERIFICADA]

    @property
    def avisos(self) -> List[ResultadoReferencia]:
        return [r for r in self.resultados if r.estado == ESTADO_AVISO]

    @property
    def errores(self) -> List[ResultadoReferencia]:
        return [r for r in self.resultados if r.estado == ESTADO_ERROR]

    def ok(self, *, estricto: bool = False) -> bool:
        if self.errores:
            return False
        if estricto and self.avisos:
            return False
        return True


def _limpiar_puntuacion_final(valor: str) -> str:
    return valor.rstrip(".,;:)]}>")


def extraer_doi(texto: str) -> Optional[str]:
    """Extrae el primer DOI presente en una entrada bibliográfica."""
    m = _RE_DOI.search(texto)
    if not m:
        return None
    return _limpiar_puntuacion_final(m.group(1))


def extraer_url(texto: str) -> Optional[str]:
    """Extrae la primera URL HTTP/HTTPS presente en una entrada bibliográfica."""
    m = _RE_URL.search(texto)
    if not m:
        return None
    return _limpiar_puntuacion_final(m.group(0))


def extraer_anio(texto: str) -> Optional[int]:
    """Extrae el año de publicación más probable (prioriza formato '(2021)' o ', 2021')."""
    m_par = re.search(r"\(((?:19|20)\d{2})[a-z]?\)", texto)
    if m_par:
        return int(m_par.group(1))
    anios = [int(a) for a in _RE_ANIO.findall(texto)]
    return anios[0] if anios else None


def extraer_tokens_significativos(texto: str) -> set[str]:
    """Extrae palabras normalizadas (>= 4 caracteres, sin stopwords) para cotejo semántico."""
    norm = rub.normalizar(texto)
    return {
        tok
        for tok in re.findall(r"[a-z0-9]{4,}", norm)
        if tok not in _PALABRAS_STOP and not tok.isdigit()
    }


def extraer_consulta_titulo_autor(texto: str) -> Tuple[str, str]:
    """Extrae un título candidato y el primer apellido para búsquedas en OpenAlex/OpenLibrary."""
    limpio = _RE_PREFIJO_NUM.sub("", texto).strip()
    limpio = _RE_URL.sub("", limpio).replace("*", "").strip()
    limpio = re.sub(r"\(\s*\d+\s*\.?\s*(?:[aª]|st|nd|rd|th)?\s*ed\.?\s*\)", "", limpio, flags=re.I)

    # Primer apellido (antes de coma o primer token con letras)
    primer_apellido = ""
    m_ap = re.match(r"^([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\-]{3,})", limpio)
    if m_ap:
        primer_apellido = rub.normalizar(m_ap.group(1))

    # 1. Estilo IEEE: título entre comillas "..."
    m_com = re.search(r'"([^"]{8,})"', limpio)
    if m_com:
        return m_com.group(1).strip(" ,."), primer_apellido

    # 2. Estilo APA 7: Autor (2021). Título de la obra. Editorial.
    m_apa = re.search(r"\((?:19|20)\d{2}[a-z]?\)\.\s*([^.]{6,})", limpio)
    if m_apa:
        return m_apa.group(1).strip(" ,."), primer_apellido

    # 3. Estilo Vancouver u otros: segundo segmento separado por punto
    partes = [p.strip() for p in limpio.split(".") if len(p.strip()) >= 8]
    if len(partes) >= 2:
        return partes[1], primer_apellido
    return limpio[:140], primer_apellido


def _http_fetch_defecto(url: str, metodo: str = "GET", timeout: float = TIMEOUT_DEFECTO) -> RespuestaHTTP:
    """Cliente HTTP por defecto basado únicamente en urllib.request."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html;q=0.8, */*;q=0.5",
    }
    req = urllib.request.Request(url, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200) or 200
            cuerpo = ""
            if metodo == "GET":
                raw = resp.read(256 * 1024)
                cuerpo = raw.decode("utf-8", errors="replace")
            return RespuestaHTTP(status=int(status), cuerpo=cuerpo, url_final=resp.geturl())
    except urllib.error.HTTPError as exc:
        return RespuestaHTTP(status=int(exc.code), error=str(exc.reason))
    except urllib.error.URLError as exc:
        return RespuestaHTTP(status=0, error=str(exc.reason))
    except TimeoutError:
        return RespuestaHTTP(status=0, error="timeout")
    except Exception as exc:  # pragma: no cover - errores de socket/SSL del SO
        return RespuestaHTTP(status=0, error=str(exc))


def _similitud_titulo(ref_texto: str, titulo_remoto: str) -> float:
    toks_remoto = extraer_tokens_significativos(titulo_remoto)
    if not toks_remoto:
        return 0.0
    toks_ref = extraer_tokens_significativos(ref_texto)
    if not toks_ref:
        return 0.0
    return len(toks_remoto & toks_ref) / len(toks_remoto)


def _extraer_anio_crossref(msg: Dict[str, Any]) -> Optional[int]:
    for campo in ("published-print", "published-online", "issued", "created"):
        bloque = msg.get(campo)
        if isinstance(bloque, dict):
            partes = bloque.get("date-parts")
            if isinstance(partes, list) and partes and isinstance(partes[0], list) and partes[0]:
                try:
                    return int(partes[0][0])
                except (TypeError, ValueError):
                    continue
    return None


def _verificar_doi_crossref(
    indice: int,
    texto: str,
    doi: str,
    fetcher: FetcherFn,
    timeout: float,
) -> ResultadoReferencia:
    url_api = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    resp = fetcher(url_api, "GET", timeout)

    if resp.status == 404:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_ERROR,
            codigo="doi_inexistente",
            detalle=f"DOI no encontrado en Crossref (HTTP 404): {doi}",
            doi=doi,
            fuente_verificacion="Crossref",
        )
    if resp.status == 0 or resp.status >= 500 or resp.status == 429:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="error_red_crossref",
            detalle=f"No se pudo consultar Crossref para {doi} ({resp.error or f'HTTP {resp.status}'}).",
            doi=doi,
            fuente_verificacion="Crossref",
        )
    if resp.status != 200:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="http_inesperado_crossref",
            detalle=f"Respuesta inesperada de Crossref (HTTP {resp.status}) para {doi}.",
            doi=doi,
            fuente_verificacion="Crossref",
        )

    try:
        data = json.loads(resp.cuerpo)
        msg = data.get("message", {}) if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="json_invalido_crossref",
            detalle=f"Respuesta no JSON desde Crossref para {doi}.",
            doi=doi,
            fuente_verificacion="Crossref",
        )

    titulos = msg.get("title") or []
    titulo_real = str(titulos[0]).strip() if isinstance(titulos, list) and titulos else ""
    anio_real = _extraer_anio_crossref(msg)
    anio_ref = extraer_anio(texto)
    autores_msg = msg.get("author") or []
    apellidos_reales = {
        rub.normalizar(str(a.get("family", "")))
        for a in autores_msg
        if isinstance(a, dict) and a.get("family")
    }
    norm_ref = rub.normalizar(texto)
    coincide_autor = any(ap and ap in norm_ref for ap in apellidos_reales) if apellidos_reales else True
    sim = _similitud_titulo(texto, titulo_real) if titulo_real else 1.0

    # Si el DOI existe pero su título no coincide en absoluto con la referencia -> DOI reciclado/alucinado
    if titulo_real and sim < 0.35 and not (coincide_autor and sim >= 0.2):
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_ERROR,
            codigo="doi_no_coincide",
            detalle=(
                f"El DOI {doi} existe en Crossref pero corresponde a otra obra: "
                f"«{titulo_real}» ({anio_real or 's. f.'}). Posible cita fabricada o DOI reciclado."
            ),
            doi=doi,
            fuente_verificacion="Crossref",
        )

    notas: List[str] = []
    if anio_ref and anio_real and abs(anio_ref - anio_real) > 2:
        notas.append(f"año citado {anio_ref} vs Crossref {anio_real}")
    if apellidos_reales and not coincide_autor and sim < 0.75:
        notas.append("ningún apellido de Crossref aparece en la referencia")

    if notas:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="doi_discrepancia_metadatos",
            detalle=f"DOI válido ({doi}), pero con discrepancia: {'; '.join(notas)}. Obra real: «{titulo_real}».",
            doi=doi,
            fuente_verificacion="Crossref",
        )

    resumen_obra = f"«{titulo_real[:80]}»" if titulo_real else doi
    return ResultadoReferencia(
        indice=indice,
        texto=texto,
        estado=ESTADO_VERIFICADA,
        codigo="verificada_doi",
        detalle=f"DOI verificado en Crossref: {resumen_obra} ({anio_real or 's. f.'}).",
        doi=doi,
        fuente_verificacion="Crossref",
    )


def _verificar_url(
    indice: int,
    texto: str,
    url: str,
    fetcher: FetcherFn,
    timeout: float,
) -> ResultadoReferencia:
    resp = fetcher(url, "HEAD", timeout)
    if resp.status in (405, 501):
        resp = fetcher(url, "GET", timeout)

    if 200 <= resp.status < 400:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_VERIFICADA,
            codigo="url_viva",
            detalle=f"URL accesible (HTTP {resp.status}): {url}",
            url=url,
            fuente_verificacion="HTTP",
        )
    if resp.status in (404, 410):
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_ERROR,
            codigo="url_rota",
            detalle=f"Enlace roto o inexistente (HTTP {resp.status}): {url}",
            url=url,
            fuente_verificacion="HTTP",
        )
    if resp.status in (401, 403, 429):
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="url_bloqueada_bot",
            detalle=f"El servidor bloqueó la verificación automática (HTTP {resp.status}, verificar manualmente): {url}",
            url=url,
            fuente_verificacion="HTTP",
        )
    if resp.status == 0 and any(
        k in resp.error.lower() for k in ("getaddrinfo", "name or service not known", "nodename nor servname")
    ):
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_ERROR,
            codigo="dominio_inexistente",
            detalle=f"Dominio inexistente ({resp.error}): {url}",
            url=url,
            fuente_verificacion="DNS/HTTP",
        )
    return ResultadoReferencia(
        indice=indice,
        texto=texto,
        estado=ESTADO_AVISO,
        codigo="url_no_verificable",
        detalle=f"No se pudo verificar la URL ({resp.error or f'HTTP {resp.status}'}): {url}",
        url=url,
        fuente_verificacion="HTTP",
    )


def _buscar_openalex(
    titulo: str,
    primer_apellido: str,
    anio_ref: Optional[int],
    ref_texto: str,
    fetcher: FetcherFn,
    timeout: float,
) -> Optional[Tuple[str, Optional[int], str]]:
    q = urllib.parse.quote(titulo)
    url = f"https://api.openalex.org/works?search={q}&per-page=3"
    resp = fetcher(url, "GET", timeout)
    if resp.status != 200:
        return None
    try:
        data = json.loads(resp.cuerpo)
        obras = data.get("results", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        return None

    for obra in obras:
        if not isinstance(obra, dict):
            continue
        t_real = str(obra.get("title") or "").strip()
        if not t_real:
            continue
        sim = _similitud_titulo(ref_texto, t_real)
        anio_real = obra.get("publication_year")
        autores_str = " ".join(
            str(a.get("author", {}).get("display_name", ""))
            for a in (obra.get("authorships") or [])
            if isinstance(a, dict)
        )
        autor_ok = (not primer_apellido) or (primer_apellido in rub.normalizar(autores_str))
        anio_ok = (not anio_ref) or (not anio_real) or (abs(int(anio_real) - anio_ref) <= 3)
        if sim >= 0.6 and (autor_ok or anio_ok):
            return t_real, int(anio_real) if anio_real else None, "OpenAlex"
    return None


def _buscar_openlibrary(
    titulo: str,
    primer_apellido: str,
    ref_texto: str,
    fetcher: FetcherFn,
    timeout: float,
) -> Optional[Tuple[str, Optional[int], str]]:
    params = urllib.parse.urlencode({"title": titulo, "limit": "3"})
    url = f"https://openlibrary.org/search.json?{params}"
    resp = fetcher(url, "GET", timeout)
    if resp.status != 200:
        return None
    try:
        data = json.loads(resp.cuerpo)
        docs = data.get("docs", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        return None

    for item in docs:
        if not isinstance(item, dict):
            continue
        t_real = str(item.get("title") or "").strip()
        if not t_real:
            continue
        sim = _similitud_titulo(ref_texto, t_real)
        autores = " ".join(str(a) for a in (item.get("author_name") or []))
        autor_ok = (not primer_apellido) or (primer_apellido in rub.normalizar(autores))
        anio_real = item.get("first_publish_year")
        if sim >= 0.6 and autor_ok:
            return t_real, int(anio_real) if anio_real else None, "OpenLibrary"
    return None


def verificar_referencia(
    texto: str,
    *,
    indice: int = 1,
    fetcher: Optional[FetcherFn] = None,
    timeout: float = TIMEOUT_DEFECTO,
) -> ResultadoReferencia:
    """Verifica la existencia real de una única referencia bibliográfica."""
    fn = fetcher or _http_fetch_defecto
    doi = extraer_doi(texto)
    if doi:
        return _verificar_doi_crossref(indice, texto, doi, fn, timeout)

    url = extraer_url(texto)
    if url:
        return _verificar_url(indice, texto, url, fn, timeout)

    titulo, primer_apellido = extraer_consulta_titulo_autor(texto)
    anio_ref = extraer_anio(texto)
    if len(titulo) < 6:
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_AVISO,
            codigo="referencia_incompleta",
            detalle="Entrada demasiado corta o sin título identificable; requiere revisión manual.",
        )

    coincidencia = _buscar_openalex(titulo, primer_apellido, anio_ref, texto, fn, timeout)
    if not coincidencia:
        coincidencia = _buscar_openlibrary(titulo, primer_apellido, texto, fn, timeout)

    if coincidencia:
        t_real, anio_real, fuente = coincidencia
        return ResultadoReferencia(
            indice=indice,
            texto=texto,
            estado=ESTADO_VERIFICADA,
            codigo=f"verificada_{fuente.lower()}",
            detalle=f"Obra encontrada en {fuente}: «{t_real[:80]}» ({anio_real or 's. f.'}).",
            fuente_verificacion=fuente,
        )

    return ResultadoReferencia(
        indice=indice,
        texto=texto,
        estado=ESTADO_AVISO,
        codigo="no_verificada_catalogo",
        detalle=(
            f"Sin DOI/URL y sin coincidencia concluyente en OpenAlex/OpenLibrary para «{titulo[:65]}». "
            "Verificar manualmente que la obra exista y no sea alucinada."
        ),
        fuente_verificacion="OpenAlex/OpenLibrary",
    )


def verificar_referencias(
    referencias: List[str],
    *,
    fetcher: Optional[FetcherFn] = None,
    timeout: float = TIMEOUT_DEFECTO,
    max_workers: int = 4,
) -> InformeVerificacionCitas:
    """Verifica en paralelo una lista de referencias bibliográficas."""
    if not referencias:
        return InformeVerificacionCitas()

    fn = fetcher or _http_fetch_defecto
    if max_workers <= 1 or len(referencias) == 1:
        resultados = [
            verificar_referencia(ref, indice=idx, fetcher=fn, timeout=timeout)
            for idx, ref in enumerate(referencias, 1)
        ]
        return InformeVerificacionCitas(resultados=resultados)

    resultados_map: Dict[int, ResultadoReferencia] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(referencias))) as pool:
        futuros = {
            pool.submit(verificar_referencia, ref, indice=idx, fetcher=fn, timeout=timeout): idx
            for idx, ref in enumerate(referencias, 1)
        }
        for fut in concurrent.futures.as_completed(futuros):
            idx = futuros[fut]
            resultados_map[idx] = fut.result()

    return InformeVerificacionCitas(resultados=[resultados_map[i] for i in range(1, len(referencias) + 1)])


def verificar_docx(
    ruta_docx: Path,
    *,
    fetcher: Optional[FetcherFn] = None,
    timeout: float = TIMEOUT_DEFECTO,
    max_workers: int = 4,
) -> InformeVerificacionCitas:
    """Extrae la sección de Referencias de un `.docx` y verifica cada entrada."""
    analisis = comp.analizar(Path(ruta_docx))
    return verificar_referencias(
        analisis.referencias,
        fetcher=fetcher,
        timeout=timeout,
        max_workers=max_workers,
    )


def imprimir_informe(informe: InformeVerificacionCitas, *, origen: str = "") -> None:
    """Imprime en consola un reporte sobrio y legible de la auditoría bibliográfica real."""
    cabecera = f"Verificación real de citas bibliográficas ({origen})" if origen else "Verificación real de citas bibliográficas"
    print(cabecera)
    print("-" * len(cabecera))
    if not informe.resultados:
        print("  No se encontraron entradas en la sección de Referencias.")
        return

    etiquetas = {
        ESTADO_VERIFICADA: "[OK]   ",
        ESTADO_AVISO: "[AVISO]",
        ESTADO_ERROR: "[ERROR]",
    }
    for res in informe.resultados:
        resumen = res.texto if len(res.texto) <= 95 else res.texto[:92] + "..."
        print(f"  {etiquetas[res.estado]} #{res.indice}: {resumen}")
        print(f"           {res.detalle}")

    print(
        f"\nResumen bibliográfico: {len(informe.verificadas)} verificadas | "
        f"{len(informe.avisos)} avisos (revisión manual) | {len(informe.errores)} errores."
    )
