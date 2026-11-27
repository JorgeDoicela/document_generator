# -*- coding: utf-8 -*-
"""Motor de renderizado de diagramas de flujo vectoriales de alta fidelidad.
Genera diagramas de flujo bajo norma ANSI/ISO con simbología formal:
- Terminal (Inicio / Fin): Óvalo / Rectángulo redondeado
- Entrada / Salida (I/O): Paralelogramo inclinado
- Proceso / Asignación: Rectángulo
- Decisión: Rombo con ramas Sí / No
Renderiza a escala 2x con antialiasing Lanczos para inserción editorial en Word y PDF.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from plantillas import plataforma  # noqa: E402


class PaletaDiagrama:
    FONDO = (255, 255, 255)
    BORDE_GENERAL = (40, 50, 70)
    FLECHA = (40, 50, 70)
    TEXTO_GENERAL = (20, 25, 35)

    # Nodos
    INICIO_FONDO = (220, 245, 230)      # Verde suave
    INICIO_BORDE = (34, 139, 34)
    FIN_FONDO = (255, 225, 225)         # Rojo suave
    FIN_BORDE = (200, 40, 40)
    PROCESO_FONDO = (235, 242, 250)     # Azul cielo suave
    PROCESO_BORDE = (41, 128, 185)
    IO_FONDO = (254, 249, 231)          # Ámbar suave
    IO_BORDE = (214, 137, 16)
    DECISION_FONDO = (245, 238, 248)    # Violeta suave
    DECISION_BORDE = (142, 68, 173)


def get_font(size: int, bold: bool = False):
    font_path = plataforma.resolver_fuente_sans(bold=bold)
    if font_path is not None:
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
    return ImageFont.load_default()


def dibujar_flecha_vertical(draw: ImageDraw.ImageDraw, x: int, y1: int, y2: int, texto: str = ""):
    """Dibuja línea vertical con punta de flecha apuntando a (x, y2)."""
    draw.line([(x, y1), (x, y2)], fill=PaletaDiagrama.FLECHA, width=3)
    # Cabeza de flecha
    if y2 > y1:
        draw.polygon([(x, y2), (x - 6, y2 - 12), (x + 6, y2 - 12)], fill=PaletaDiagrama.FLECHA)
    else:
        draw.polygon([(x, y2), (x - 6, y2 + 12), (x + 6, y2 + 12)], fill=PaletaDiagrama.FLECHA)

    if texto:
        f_lbl = get_font(20, bold=True)
        draw.text((x + 8, (y1 + y2) // 2 - 10), texto, fill=PaletaDiagrama.TEXTO_GENERAL, font=f_lbl)


def dibujar_flecha_horizontal(draw: ImageDraw.ImageDraw, x1: int, y: int, x2: int, texto: str = ""):
    """Dibuja línea horizontal con punta de flecha apuntando a (x2, y)."""
    draw.line([(x1, y), (x2, y)], fill=PaletaDiagrama.FLECHA, width=3)
    if x2 > x1:
        draw.polygon([(x2, y), (x2 - 12, y - 6), (x2 - 12, y + 6)], fill=PaletaDiagrama.FLECHA)
    else:
        draw.polygon([(x2, y), (x2 + 12, y - 6), (x2 + 12, y + 6)], fill=PaletaDiagrama.FLECHA)

    if texto:
        f_lbl = get_font(20, bold=True)
        draw.text(((x1 + x2) // 2 - 15, y - 26), texto, fill=PaletaDiagrama.TEXTO_GENERAL, font=f_lbl)


def dibujar_terminal(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, texto: str, es_fin: bool = False):
    """Nodo Terminal (Inicio / Fin)."""
    bg = PaletaDiagrama.FIN_FONDO if es_fin else PaletaDiagrama.INICIO_FONDO
    borde = PaletaDiagrama.FIN_BORDE if es_fin else PaletaDiagrama.INICIO_BORDE
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=h // 2, fill=bg, outline=borde, width=3)
    font = get_font(22, bold=True)
    bbox = draw.textbbox((0, 0), texto, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), texto, fill=PaletaDiagrama.TEXTO_GENERAL, font=font)


def dibujar_proceso(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, lineas: list[str]):
    """Nodo Proceso (Cálculo / Asignación)."""
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    draw.rectangle([(x1, y1), (x2, y2)], fill=PaletaDiagrama.PROCESO_FONDO, outline=PaletaDiagrama.PROCESO_BORDE, width=3)
    font = get_font(20, bold=False)
    total_h = len(lineas) * 26
    start_y = cy - total_h // 2
    for idx, linea in enumerate(lineas):
        bbox = draw.textbbox((0, 0), linea, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, start_y + idx * 26), linea, fill=PaletaDiagrama.TEXTO_GENERAL, font=font)


def dibujar_io(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, lineas: list[str]):
    """Nodo Entrada/Salida (Paralelogramo inclinado)."""
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    skew = 24
    puntos = [(x1 + skew, y1), (x2, y1), (x2 - skew, y2), (x1, y2)]
    draw.polygon(puntos, fill=PaletaDiagrama.IO_FONDO, outline=PaletaDiagrama.IO_BORDE)
    # Redibujar bordes limpios
    draw.line(puntos + [puntos[0]], fill=PaletaDiagrama.IO_BORDE, width=3)
    font = get_font(20, bold=False)
    total_h = len(lineas) * 26
    start_y = cy - total_h // 2
    for idx, linea in enumerate(lineas):
        bbox = draw.textbbox((0, 0), linea, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, start_y + idx * 26), linea, fill=PaletaDiagrama.TEXTO_GENERAL, font=font)


def dibujar_decision(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, condicion: str):
    """Nodo Decisión (Rombo)."""
    puntos = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
    draw.polygon(puntos, fill=PaletaDiagrama.DECISION_FONDO, outline=PaletaDiagrama.DECISION_BORDE)
    draw.line(puntos + [puntos[0]], fill=PaletaDiagrama.DECISION_BORDE, width=3)
    font = get_font(21, bold=True)
    bbox = draw.textbbox((0, 0), condicion, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), condicion, fill=PaletaDiagrama.TEXTO_GENERAL, font=font)


def generar_diagrama_comparacion(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para comparación de dos valores con tricotomía."""
    W, H = 1000, 1050
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 500
    # 1. Inicio
    dibujar_terminal(draw, cx, 60, 260, 56, "Inicio: MayorDeDos")
    dibujar_flecha_vertical(draw, cx, 88, 140)

    # 2. Entrada
    dibujar_io(draw, cx, 175, 360, 70, ["Leer num1 (entero)", "Leer num2 (entero)"])
    dibujar_flecha_vertical(draw, cx, 210, 275)

    # 3. Decisión 1: num1 > num2
    dibujar_decision(draw, cx, 335, 280, 110, "¿num1 > num2?")

    # Rama Sí de Decisión 1 -> Izquierda
    dibujar_flecha_horizontal(draw, cx - 140, 335, 220, "Sí")
    dibujar_io(draw, 220, 420, 260, 65, ['Mostrar: "Mayor es num1"'])
    draw.line([(220, 335), (220, 387)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(220, 387), (214, 375), (226, 375)], fill=PaletaDiagrama.FLECHA)

    # Rama No de Decisión 1 -> Abajo a Decisión 2
    dibujar_flecha_vertical(draw, cx, 390, 475, "No")

    # 4. Decisión 2: num2 > num1
    dibujar_decision(draw, cx, 535, 280, 110, "¿num2 > num1?")

    # Rama Sí de Decisión 2 -> Derecha
    dibujar_flecha_horizontal(draw, cx + 140, 535, 780, "Sí")
    dibujar_io(draw, 780, 620, 260, 65, ['Mostrar: "Mayor es num2"'])
    draw.line([(780, 535), (780, 587)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(780, 587), (774, 575), (786, 575)], fill=PaletaDiagrama.FLECHA)

    # Rama No de Decisión 2 -> Abajo (Igualdad)
    dibujar_flecha_vertical(draw, cx, 590, 675, "No")
    dibujar_io(draw, cx, 715, 340, 65, ['Mostrar: "Son iguales (num1 = num2)"'])

    # Convergencia a Fin
    dibujar_flecha_vertical(draw, cx, 748, 880)

    # Rutas de salida de ramas laterales hacia Fin
    draw.line([(220, 453), (220, 830), (cx - 150, 830)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.line([(780, 653), (780, 830), (cx + 150, 830)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.line([(cx - 150, 830), (cx, 830)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.line([(cx + 150, 830), (cx, 830)], fill=PaletaDiagrama.FLECHA, width=3)

    # 5. Fin
    dibujar_terminal(draw, cx, 910, 220, 56, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def generar_diagrama_promedio(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para cálculo de promedio y clasificación."""
    W, H = 900, 950
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 450
    # 1. Inicio
    dibujar_terminal(draw, cx, 55, 300, 56, "Inicio: PromedioCalificaciones")
    dibujar_flecha_vertical(draw, cx, 83, 135)

    # 2. Entrada
    dibujar_io(draw, cx, 180, 460, 80, ["Leer nombre (cadena)", "Leer nota1, nota2, nota3 (reales [0-10])"])
    dibujar_flecha_vertical(draw, cx, 220, 275)

    # 3. Proceso cálculo
    dibujar_proceso(draw, cx, 315, 420, 70, ["promedio <- (nota1 + nota2 + nota3) / 3"])
    dibujar_flecha_vertical(draw, cx, 350, 415)

    # 4. Decisión
    dibujar_decision(draw, cx, 475, 300, 110, "¿promedio >= 7.0?")

    # Rama Sí -> Aprobado (Izquierda)
    dibujar_flecha_horizontal(draw, cx - 150, 475, 200, "Sí")
    draw.line([(200, 475), (200, 555)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(200, 555), (194, 543), (206, 543)], fill=PaletaDiagrama.FLECHA)
    dibujar_io(draw, 200, 600, 310, 80, ["Mostrar: nombre, promedio", 'Mostrar: "APROBADO"'])

    # Rama No -> Reprobado (Derecha)
    dibujar_flecha_horizontal(draw, cx + 150, 475, 700, "No")
    draw.line([(700, 475), (700, 555)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(700, 555), (694, 543), (706, 543)], fill=PaletaDiagrama.FLECHA)
    dibujar_io(draw, 700, 600, 310, 80, ["Mostrar: nombre, promedio", 'Mostrar: "REPROBADO"'])

    # Convergencia a Fin
    draw.line([(200, 640), (200, 740), (cx, 740)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.line([(700, 640), (700, 740), (cx, 740)], fill=PaletaDiagrama.FLECHA, width=3)
    dibujar_flecha_vertical(draw, cx, 740, 805)

    # 5. Fin
    dibujar_terminal(draw, cx, 835, 220, 56, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def generar_diagrama_estadisticas_lista(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para estadísticas sobre una lista de 10 enteros."""
    W, H = 1000, 1400
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 500
    # 1. Inicio
    dibujar_terminal(draw, cx, 50, 300, 54, "Inicio: ListaDiezEnteros")
    dibujar_flecha_vertical(draw, cx, 77, 125)

    # 2. Inicialización primer elemento
    dibujar_io(draw, cx, 160, 360, 60, ["Leer numero[1]"])
    dibujar_flecha_vertical(draw, cx, 190, 235)

    dibujar_proceso(draw, cx, 280, 480, 80, [
        "suma <- numero[1]",
        "mayor <- numero[1]",
        "menor <- numero[1]",
        "i <- 2"
    ])
    dibujar_flecha_vertical(draw, cx, 320, 375)

    # 3. Bucle: ¿i <= 10?
    dibujar_decision(draw, cx, 430, 260, 100, "¿i <= 10?")

    # Rama Sí (dentro del bucle) -> Abajo
    dibujar_flecha_vertical(draw, cx, 480, 530, "Sí")
    dibujar_io(draw, cx, 560, 320, 54, ["Leer numero[i]"])
    dibujar_flecha_vertical(draw, cx, 587, 630)

    dibujar_proceso(draw, cx, 660, 340, 54, ["suma <- suma + numero[i]"])
    dibujar_flecha_vertical(draw, cx, 687, 730)

    # Actualización mayor
    dibujar_decision(draw, cx, 780, 280, 95, "¿numero[i] > mayor?")
    dibujar_flecha_horizontal(draw, cx + 140, 780, 780, "Sí")
    dibujar_proceso(draw, 780, 780, 220, 50, ["mayor <- numero[i]"])
    draw.line([(780, 805), (780, 860), (cx, 860)], fill=PaletaDiagrama.FLECHA, width=3)
    dibujar_flecha_vertical(draw, cx, 828, 860, "No")

    # Actualización menor
    dibujar_flecha_vertical(draw, cx, 860, 905)
    dibujar_decision(draw, cx, 950, 280, 95, "¿numero[i] < menor?")
    dibujar_flecha_horizontal(draw, cx + 140, 950, 780, "Sí")
    dibujar_proceso(draw, 780, 950, 220, 50, ["menor <- numero[i]"])
    draw.line([(780, 975), (780, 1030), (cx, 1030)], fill=PaletaDiagrama.FLECHA, width=3)
    dibujar_flecha_vertical(draw, cx, 998, 1030, "No")

    # Incremento i
    dibujar_flecha_vertical(draw, cx, 1030, 1065)
    dibujar_proceso(draw, cx, 1095, 240, 54, ["i <- i + 1"])

    # Retorno al bucle (Línea hacia la izquierda y arriba hasta 430)
    draw.line([(cx - 120, 1095), (120, 1095), (120, 430), (cx - 130, 430)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx - 130, 430), (cx - 142, 424), (cx - 142, 436)], fill=PaletaDiagrama.FLECHA)

    # Rama No del bucle (Sale a la derecha desde 430) -> Salida de resultados
    draw.line([(cx + 130, 430), (890, 430), (890, 1140), (cx + 250, 1140)], fill=PaletaDiagrama.FLECHA, width=3)
    f_lbl = get_font(20, bold=True)
    draw.text((cx + 145, 405), "No", fill=PaletaDiagrama.TEXTO_GENERAL, font=f_lbl)

    dibujar_proceso(draw, cx, 1170, 360, 54, ["promedio <- suma / 10"])
    dibujar_flecha_vertical(draw, cx, 1197, 1225)
    draw.line([(cx + 250, 1140), (cx, 1140)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx, 1140), (cx + 12, 1134), (cx + 12, 1146)], fill=PaletaDiagrama.FLECHA)

    dibujar_io(draw, cx, 1255, 460, 54, ["Mostrar: suma, promedio, mayor, menor"])
    dibujar_flecha_vertical(draw, cx, 1282, 1315)

    # 4. Fin
    dibujar_terminal(draw, cx, 1345, 200, 50, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def generar_diagrama_calculo_secuencial(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para un flujo secuencial simple de entrada/proceso/salida."""
    W, H = 850, 750
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 425
    # 1. Inicio
    dibujar_terminal(draw, cx, 55, 260, 54, "Inicio: CalculoEdad")
    dibujar_flecha_vertical(draw, cx, 82, 135)

    # 2. Entrada
    dibujar_io(draw, cx, 180, 460, 80, ["Leer nombre (cadena)", "Leer anio_nacimiento, anio_actual (enteros)"])
    dibujar_flecha_vertical(draw, cx, 220, 275)

    # 3. Proceso
    dibujar_proceso(draw, cx, 315, 380, 70, ["edad <- anio_actual - anio_nacimiento"])
    dibujar_flecha_vertical(draw, cx, 350, 415)

    # 4. Salida
    dibujar_io(draw, cx, 460, 420, 80, ['Mostrar: "Usuario:", nombre', 'Mostrar: "Edad calculada:", edad, "años"'])
    dibujar_flecha_vertical(draw, cx, 500, 570)

    # 5. Fin
    dibujar_terminal(draw, cx, 600, 220, 54, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def generar_diagrama_autenticacion(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para autenticación con límite de reintentos y bloqueo."""
    W, H = 1000, 1100
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 500
    # 1. Inicio
    dibujar_terminal(draw, cx, 55, 320, 54, "Inicio: AutenticacionBloqueo")
    dibujar_flecha_vertical(draw, cx, 82, 135)

    # 2. Inicialización
    dibujar_proceso(draw, cx, 180, 460, 80, [
        'usuario_valido <- "admin"',
        'clave_valida <- "1234"',
        "intentos <- 0, max_intentos <- 3"
    ])
    dibujar_flecha_vertical(draw, cx, 220, 275)

    # 3. Bucle condición intentos < max_intentos
    dibujar_decision(draw, cx, 335, 320, 110, "¿intentos < max_intentos?")

    # Rama Sí -> Leer credenciales (Abajo)
    dibujar_flecha_vertical(draw, cx, 390, 440, "Sí")
    dibujar_io(draw, cx, 475, 340, 60, ["Leer usuario, clave"])
    dibujar_flecha_vertical(draw, cx, 505, 550)

    # Decisión credenciales correctas
    dibujar_decision(draw, cx, 610, 360, 110, "¿user == val Y clave == val?")

    # Rama Sí credenciales correctas -> Acceso concedido (Izquierda)
    dibujar_flecha_horizontal(draw, cx - 180, 610, 200, "Sí")
    draw.line([(200, 610), (200, 690)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(200, 690), (194, 678), (206, 678)], fill=PaletaDiagrama.FLECHA)
    dibujar_io(draw, 200, 735, 300, 80, ['Mostrar: "Ingreso Exitoso"', 'Mostrar: "Bienvenido al Sistema"'])
    draw.line([(200, 775), (200, 940), (cx, 940)], fill=PaletaDiagrama.FLECHA, width=3)

    # Rama No credenciales correctas -> Reintento / Incremento (Derecha)
    dibujar_flecha_horizontal(draw, cx + 180, 610, 800, "No")
    draw.line([(800, 610), (800, 680)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(800, 680), (794, 668), (806, 668)], fill=PaletaDiagrama.FLECHA)
    dibujar_proceso(draw, 800, 725, 260, 80, [
        "intentos <- intentos + 1",
        'Mostrar: "Datos Incorrectos"'
    ])
    # Retorno al bucle de arriba
    draw.line([(800, 765), (800, 840), (940, 840), (940, 335), (cx + 160, 335)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx + 160, 335), (cx + 172, 329), (cx + 172, 341)], fill=PaletaDiagrama.FLECHA)

    # Rama No del bucle principal (intentos >= max_intentos) -> Bloqueo
    draw.line([(cx - 160, 335), (80, 335), (80, 860), (cx - 200, 860)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx - 200, 860), (cx - 212, 854), (cx - 212, 866)], fill=PaletaDiagrama.FLECHA)
    f_lbl = get_font(20, bold=True)
    draw.text((cx - 185, 310), "No", fill=PaletaDiagrama.TEXTO_GENERAL, font=f_lbl)

    dibujar_io(draw, cx, 860, 380, 75, [
        'Mostrar: "Usuario Bloqueado"',
        'Mostrar: "Intentos Agotados (3 de 3)"'
    ])
    dibujar_flecha_vertical(draw, cx, 898, 975)

    # Fin
    dibujar_terminal(draw, cx, 1010, 220, 54, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def generar_diagrama_validacion_iterativa(ruta_salida: Path):
    """Genera diagrama de flujo ANSI/ISO para validación de rango y generación iterativa."""
    W, H = 900, 1050
    img = Image.new("RGB", (W, H), PaletaDiagrama.FONDO)
    draw = ImageDraw.Draw(img)

    cx = 450
    # 1. Inicio
    dibujar_terminal(draw, cx, 50, 300, 54, "Inicio: TablaMultiplicar")
    dibujar_flecha_vertical(draw, cx, 77, 125)

    # 2. Entrada y validación
    dibujar_io(draw, cx, 160, 340, 60, ["Leer numero (entero)"])
    dibujar_flecha_vertical(draw, cx, 190, 235)

    dibujar_decision(draw, cx, 290, 320, 100, "¿2 <= numero <= 12?")

    # Rama No validación -> Reintento
    dibujar_flecha_horizontal(draw, cx + 160, 290, 750, "No")
    dibujar_io(draw, 750, 290, 240, 60, ['Mostrar: "Fuera de rango"'])
    draw.line([(750, 260), (750, 160), (cx + 170, 160)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx + 170, 160), (cx + 182, 154), (cx + 182, 166)], fill=PaletaDiagrama.FLECHA)

    # Rama Sí validación -> Inicializar bucle de tabla
    dibujar_flecha_vertical(draw, cx, 340, 395, "Sí")
    dibujar_proceso(draw, cx, 430, 240, 60, ["i <- 1"])
    dibujar_flecha_vertical(draw, cx, 460, 515)

    # Bucle multiplicación
    dibujar_decision(draw, cx, 570, 260, 100, "¿i <= 12?")

    # Rama Sí del bucle -> Cálculo y muestra
    dibujar_flecha_vertical(draw, cx, 620, 675, "Sí")
    dibujar_proceso(draw, cx, 715, 320, 65, [
        "producto <- numero * i",
        "i <- i + 1"
    ])
    dibujar_flecha_vertical(draw, cx, 748, 800)
    dibujar_io(draw, cx, 835, 340, 60, ['Mostrar: numero, "x", (i-1), "=", producto'])

    # Retorno al bucle de multiplicación
    draw.line([(cx - 170, 835), (150, 835), (150, 570), (cx - 130, 570)], fill=PaletaDiagrama.FLECHA, width=3)
    draw.polygon([(cx - 130, 570), (cx - 142, 564), (cx - 142, 576)], fill=PaletaDiagrama.FLECHA)

    # Rama No del bucle -> Fin
    dibujar_flecha_horizontal(draw, cx + 130, 570, 750, "No")
    draw.line([(750, 570), (750, 920), (cx, 920)], fill=PaletaDiagrama.FLECHA, width=3)
    dibujar_flecha_vertical(draw, cx, 920, 965)

    dibujar_terminal(draw, cx, 995, 220, 54, "Fin", es_fin=True)

    img.save(ruta_salida, "PNG", optimize=True)
    print(f"[OK] Diagrama generado: {ruta_salida.name}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Genera diagramas de flujo ANSI/ISO de ejemplo en formato PNG."
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=RAIZ / "examples" / "diagramas_flujo",
        help="Directorio de destino para los PNG generados.",
    )
    args = parser.parse_args()
    destino = args.salida.resolve()
    destino.mkdir(parents=True, exist_ok=True)

    generar_diagrama_comparacion(destino / "diagrama_comparacion.png")
    generar_diagrama_promedio(destino / "diagrama_promedio.png")
    generar_diagrama_estadisticas_lista(destino / "diagrama_estadisticas_lista.png")
    generar_diagrama_calculo_secuencial(destino / "diagrama_calculo_secuencial.png")
    generar_diagrama_autenticacion(destino / "diagrama_autenticacion.png")
    generar_diagrama_validacion_iterativa(destino / "diagrama_validacion_iterativa.png")


if __name__ == "__main__":
    main()
