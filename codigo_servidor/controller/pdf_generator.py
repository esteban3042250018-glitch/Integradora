"""Controlador para la generación de archivos PDF con ReportLab compatible con HTML."""
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.utils import ImageReader

from controller.database_conecction import database_cursor
from model.generar_membrete import obtener_conexion, obtener_imagen_membrete
from model.folio_format import read_configuration, reportlab_font
from controller.rich_content import html_to_pdf_flowables

MARGEN_SUPERIOR_CONTENIDO = 290
POSICION_FOLIO = 566
ESPACIADO_METADATOS = 15


def cargar_membrete_activo():
    conexion = obtener_conexion()
    try:
        _, _, imagen = obtener_imagen_membrete(conexion)
        return imagen
    finally:
        conexion.close()


def cargar_configuracion_folio():
    conexion = obtener_conexion()
    try:
        with database_cursor(conexion) as cursor:
            return read_configuration(cursor)
    finally:
        conexion.close()


def dibujar_fondo_membrete(canvas, doc, imagen_bytes):
    canvas.saveState()
    try:
        canvas.drawImage(
            ImageReader(BytesIO(imagen_bytes)),
            0,
            0,
            width=612,
            height=792,
        )
    finally:
        canvas.restoreState()


def generar_pdf_oficio(ruta_pdf, folio, asunto, texto_cuerpo, area_emisora="", recepcion=""):
    """Compila el PDF aplicando el membrete, folio, asunto, área emisora, recepción y cuerpo."""
    imagen_membrete = cargar_membrete_activo()
    configuracion_folio = cargar_configuracion_folio()

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=MARGEN_SUPERIOR_CONTENIDO,
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

    story = html_to_pdf_flowables(
        texto_cuerpo, estilo_parrafo, letter[0] - 108)

    def on_first_page(canvas, doc):
        dibujar_fondo_membrete(canvas, doc, imagen_membrete)
        canvas.saveState()
        canvas.setFont(
            reportlab_font(configuracion_folio['fuente'], bold=True),
            configuracion_folio['tamano'],
        )
        canvas.drawString(54, POSICION_FOLIO, f"Oficio No. {folio}")
        canvas.setFont(
            reportlab_font(configuracion_folio['fuente']),
            configuracion_folio['tamano'],
        )
        canvas.drawString(
            54, POSICION_FOLIO - ESPACIADO_METADATOS, f"Asunto: {asunto}")
        if area_emisora:
            canvas.drawString(
                54, POSICION_FOLIO - 2 * ESPACIADO_METADATOS,
                f"Área emisora: {area_emisora}")
        if recepcion:
            canvas.drawString(
                54, POSICION_FOLIO - 3 * ESPACIADO_METADATOS,
                f"Recepción: {recepcion}")
        canvas.restoreState()

    def on_later_pages(canvas, doc):
        dibujar_fondo_membrete(canvas, doc, imagen_membrete)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)