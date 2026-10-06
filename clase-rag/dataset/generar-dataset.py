#!/usr/bin/env python3
"""Genera el corpus de prueba de la clase RAG.

Produce tres PDFs que cubren los tres casos que importan:

  01-manual-operaciones.pdf  texto normal, varias paginas
  02-tarifario-servicios.pdf texto + una tabla de precios
  03-acta-escaneada.pdf      SIN capa de texto (es una imagen)

El tercero no es un truco: se genera un PDF con texto, se rasteriza a
imagenes con pdftoppm y se vuelve a armar el PDF a partir de las
imagenes. El texto desaparece, igual que en un escaneo real.

Uso:
    python3 generar-dataset.py

Requiere: reportlab, Pillow, poppler (pdftoppm) y pypdf para verificar.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
BASE = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=BASE["Heading1"], fontSize=17, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=BASE["Heading2"], fontSize=12.5, spaceBefore=12, spaceAfter=5)
P = ParagraphStyle("P", parent=BASE["BodyText"], fontSize=10.5, leading=15, spaceAfter=5)
BULLET = ParagraphStyle("BULLET", parent=P, leftIndent=14, bulletIndent=4)
NOTA = ParagraphStyle("NOTA", parent=P, fontSize=9, textColor=colors.HexColor("#444444"))


def _doc(path: Path, titulo: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        title=titulo,
        author="Talleres Rivadavia S.A.",
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )


# ---------------------------------------------------------------------------
# 01 - Manual de operaciones (texto plano)
# ---------------------------------------------------------------------------
def manual(path: Path) -> None:
    s = []
    s.append(Paragraph("Manual de Operaciones", H1))
    s.append(Paragraph("Talleres Rivadavia S.A. &mdash; Version 4.2 &mdash; Enero 2026", NOTA))
    s.append(Spacer(1, 12))

    s.append(Paragraph("1. Alcance", H2))
    s.append(Paragraph(
        "Este manual aplica a todas las sucursales de Talleres Rivadavia S.A. y regula la "
        "atencion al publico, las garantias, los descuentos autorizados y los plazos de "
        "entrega de los servicios tecnicos.", P))

    s.append(Paragraph("2. Horarios y canales de atencion", H2))
    for t in [
        "Horario de atencion al publico: lunes a viernes de 9:00 a 18:00 horas.",
        "Sabados: de 9:00 a 13:00 horas. Domingos y feriados: cerrado.",
        "Mesa de ayuda interna: extension 204, correo soporte@talleresrivadavia.com",
        "Plazo de respuesta comprometido de la mesa de ayuda: 4 horas habiles.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))

    s.append(PageBreak())
    s.append(Paragraph("3. Garantias", H2))
    for t in [
        "La garantia estandar sobre reparaciones es de 18 meses contados desde la "
        "fecha de entrega del vehiculo.",
        "Los repuestos originales tienen una garantia de fabrica de 12 meses.",
        "La garantia no cubre danos por uso indebido, siniestros ni intervenciones "
        "realizadas por terceros ajenos a la red de talleres.",
        "Para hacer efectiva una garantia se debe presentar la orden de trabajo original.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))

    s.append(Paragraph("4. Descuentos y niveles de autorizacion", H2))
    for t in [
        "Hasta 10% de descuento: no requiere autorizacion.",
        "Entre 10% y 25%: requiere autorizacion del gerente de sucursal.",
        "Mas de 25%: requiere aprobacion de la direccion comercial.",
        "Ningun descuento puede aplicarse sobre el precio de los repuestos originales.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))

    s.append(Paragraph("5. Plazos de entrega", H2))
    for t in [
        "Entrega estandar: 15 dias habiles desde la recepcion del vehiculo.",
        "Servicio expres: 5 dias habiles, con un recargo del 30% sobre el precio de lista.",
        "Los plazos se suspenden mientras se espera la aprobacion del presupuesto "
        "por parte del cliente.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))

    s.append(Paragraph("6. Escalamiento de incidentes", H2))
    for t in [
        "Nivel 1: mesa de ayuda. Resuelve consultas de operacion y accesos.",
        "Nivel 2: supervisor tecnico. Interviene cuando el caso requiere diagnostico.",
        "Nivel 3: gerencia tecnica. Interviene ante fallas recurrentes o riesgo de "
        "seguridad.",
        "Un incidente critico debe escalarse a nivel 3 dentro de los 30 minutos "
        "posteriores a su deteccion.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))

    _doc(path, "Manual de Operaciones").build(s)


# ---------------------------------------------------------------------------
# 02 - Tarifario (texto + tabla)
# ---------------------------------------------------------------------------
def tarifario(path: Path) -> None:
    s = []
    s.append(Paragraph("Tarifario de Servicios 2026", H1))
    s.append(Paragraph("Talleres Rivadavia S.A. &mdash; Vigente desde el 1 de enero de 2026", NOTA))
    s.append(Spacer(1, 14))
    s.append(Paragraph(
        "Precios de lista expresados en pesos mexicanos. No incluyen IVA.", P))
    s.append(Spacer(1, 8))

    datos = [
        ["Codigo", "Servicio", "Plazo", "Precio MXN"],
        ["SRV-100", "Diagnostico general", "1 dia habil", "850"],
        ["SRV-210", "Service basico", "5 dias habiles", "2,400"],
        ["SRV-220", "Service premium", "5 dias habiles", "5,900"],
        ["SRV-310", "Reparacion de transmision", "15 dias habiles", "18,750"],
        ["SRV-410", "Pintura por panel", "10 dias habiles", "3,200"],
        ["SRV-500", "Traslado en grua (por kilometro)", "inmediato", "42"],
    ]
    t = Table(datos, colWidths=[2.4 * cm, 7.4 * cm, 3.6 * cm, 2.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8a8a8a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef1f7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    s.append(t)
    s.append(Spacer(1, 14))

    s.append(Paragraph("Notas del tarifario", H2))
    for txt in [
        "El precio del service premium incluye cambio de aceite sintetico y revision "
        "de 40 puntos de seguridad.",
        "El traslado en grua se cobra por kilometro recorrido y no tiene tope minimo.",
        "Los precios de lista pueden sufrir variaciones sin previo aviso.",
    ]:
        s.append(Paragraph(txt, BULLET, bulletText="\u2022"))

    _doc(path, "Tarifario de Servicios 2026").build(s)


# ---------------------------------------------------------------------------
# 03 - Acta escaneada (se rasteriza: queda SIN capa de texto)
# ---------------------------------------------------------------------------
def _fuente_acta(path: Path) -> None:
    s = []
    s.append(Paragraph("Anexo A &mdash; Acta de Inspeccion Tecnica", H1))
    s.append(Paragraph("Acta N.&ordm; A-2026-014", NOTA))
    s.append(Spacer(1, 16))
    s.append(Paragraph("Datos del lote inspeccionado", H2))
    for t in [
        "Lote: L-2026-014",
        "Fecha de inspeccion: 12 de febrero de 2026",
        "Responsable: Ing. Marta Quiroga, gerencia tecnica.",
    ]:
        s.append(Paragraph(t, BULLET, bulletText="\u2022"))
    s.append(Paragraph("Resultado", H2))
    s.append(Paragraph(
        "El lote L-2026-014 fue RECHAZADO por exceso de humedad. La medicion arrojo "
        "12.4%, cuando el maximo permitido por la norma interna es de 8%.", P))
    s.append(Paragraph("Acciones tomadas", H2))
    s.append(Paragraph(
        "Se notifico al proveedor y se bloqueo la liberacion del lote hasta una nueva "
        "inspeccion. Se programo la reinspeccion para el 26 de febrero de 2026.", P))
    _doc(path, "Acta de Inspeccion A-2026-014").build(s)


def acta_escaneada(path: Path) -> None:
    if not shutil.which("pdftoppm"):
        raise RuntimeError(
            "Falta pdftoppm (poppler). En macOS: brew install poppler")
    from PIL import Image, ImageEnhance

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        fuente = tmpdir / "acta.pdf"
        _fuente_acta(fuente)

        subprocess.run(
            ["pdftoppm", "-r", "150", "-png", str(fuente), str(tmpdir / "pagina")],
            check=True,
        )

        paginas = sorted(tmpdir.glob("pagina-*.png"))
        if not paginas:
            raise RuntimeError("pdftoppm no genero ninguna imagen")

        imagenes = []
        for pg in paginas:
            img = Image.open(pg).convert("L")
            img = ImageEnhance.Contrast(img).enhance(0.82)
            # Una inclinacion leve: lo que hace un alimentador de hojas.
            img = img.rotate(
                -0.7, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255
            )
            imagenes.append(img)

        imagenes[0].save(
            path,
            save_all=True,
            append_images=imagenes[1:],
            resolution=150.0,
        )


# ---------------------------------------------------------------------------
# Verificacion: cuanto texto tiene cada PDF
# ---------------------------------------------------------------------------
def verificar() -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  (pypdf no instalado: no se puede verificar la capa de texto)")
        return 0

    print()
    print(f"  {'ARCHIVO':<30} {'PAGINAS':>8} {'CARACTERES DE TEXTO':>21}")
    print(f"  {'-' * 30} {'-' * 8} {'-' * 21}")
    fallos = 0
    for nombre in [
        "01-manual-operaciones.pdf",
        "02-tarifario-servicios.pdf",
        "03-acta-escaneada.pdf",
    ]:
        ruta = DIR / nombre
        lector = PdfReader(str(ruta))
        texto = "".join(p.extract_text() or "" for p in lector.pages)
        print(f"  {nombre:<30} {len(lector.pages):>8} {len(texto.strip()):>21}")
        if "escaneada" in nombre and len(texto.strip()) > 50:
            print("    ERROR: el PDF escaneado igual tiene capa de texto")
            fallos += 1
        if "escaneada" not in nombre and len(texto.strip()) < 500:
            print("    ERROR: este PDF deberia tener texto y casi no tiene")
            fallos += 1
    return fallos


def main() -> int:
    print("Generando corpus en", DIR)
    manual(DIR / "01-manual-operaciones.pdf")
    print("  ok  01-manual-operaciones.pdf")
    tarifario(DIR / "02-tarifario-servicios.pdf")
    print("  ok  02-tarifario-servicios.pdf")
    acta_escaneada(DIR / "03-acta-escaneada.pdf")
    print("  ok  03-acta-escaneada.pdf  (rasterizado, sin capa de texto)")

    fallos = verificar()
    if fallos:
        print(f"\n{fallos} verificacion(es) fallaron.")
        return 1
    print("\nCorpus listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
