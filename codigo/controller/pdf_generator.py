"""Controlador para la generación de archivos PDF con ReportLab compatible con HTML."""
import os
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

# Carpeta "codigo" (este archivo está en codigo/controller/)
RAIZ = Path(__file__).resolve().parent.parent
RUTA_MEMBRETE = RAIZ / "icon.png"


def dibujar_fondo_membrete(canvas, doc):
    canvas.saveState()
    if RUTA_MEMBRETE.is_file():
        canvas.drawImage(str(RUTA_MEMBRETE), 0, 0, width=612, height=792)
    else:
        print(f"Alerta: No se encontró el membrete '{RUTA_MEMBRETE}'. Se usará fondo blanco.")
    canvas.restoreState()


def limpiar_html_para_reportlab(html_texto):
    """Convierte y limpia etiquetas HTML para que ReportLab las procese sin errores de sintaxis."""
    if not html_texto or not html_texto.strip():
        return ["&nbsp;"]

    texto = html_texto.replace('<br>', '<br/>').replace('</br>', '')
    texto = texto.replace('</p>', '<br/><br/>').replace('<p>', '')

    texto = texto.replace('<strong>', '<b>').replace('</strong>', '</b>')
    texto = texto.replace('<em>', '<i>').replace('</em>', '</i>')
    texto = texto.replace('<ul>', '').replace('</ul>', '')
    texto = texto.replace('<li>', '• ').replace('</li>', '<br/>')

    lineas = texto.split('<br/>')
    parrafos_finales = []
    for l in lineas:
        l_limpia = l.strip()
        parrafos_finales.append(l_limpia if l_limpia else "&nbsp;")

    return parrafos_finales


def generar_pdf_oficio(ruta_pdf, folio, asunto, texto_cuerpo, area_emisora="", recepcion=""):
    """Compila el PDF aplicando el membrete, folio, asunto, área emisora, recepción y cuerpo."""
    print("PDF (cuerpo recibido):", repr((texto_cuerpo or "")[:300]))

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=230,
        bottomMargin=110,
    )

    styles = getSampleStyleSheet()
    estilo_parrafo = ParagraphStyle(
        'EstiloOficio',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )

    story = []
    for linea in limpiar_html_para_reportlab(texto_cuerpo):
        story.append(Paragraph(linea, estilo_parrafo))

    def on_first_page(canvas, doc):
        dibujar_fondo_membrete(canvas, doc)
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(54, 645, f"Oficio No. {folio}")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(54, 630, f"Asunto: {asunto}")
        # El cuerpo empieza en y≈562 (792 - topMargin); estas líneas quedan entre el asunto y el cuerpo.
        # Si chocan con tu membrete, ajusta estas coordenadas.
        if area_emisora:
            canvas.drawString(54, 615, f"Área emisora: {area_emisora}")
        if recepcion:
            canvas.drawString(54, 600, f"Recepción: {recepcion}")
        canvas.restoreState()

    def on_later_pages(canvas, doc):
        dibujar_fondo_membrete(canvas, doc)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)