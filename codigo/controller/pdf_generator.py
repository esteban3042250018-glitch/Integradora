"""Controlador para la generación de archivos PDF con ReportLab compatible con HTML."""
import os
import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY


def dibujar_fondo_membrete(canvas, doc):
    canvas.saveState()
    ruta_membrete = "C:/Users/nabet/Desktop/POO/icon.png"
    
    if os.path.exists(ruta_membrete):
        canvas.drawImage(ruta_membrete, 0, 0, width=612, height=792)
    else:
        print(f"Alerta: No se encontró el archivo '{ruta_membrete}'. Se usará fondo blanco.")
        
    canvas.restoreState()


def limpiar_html_para_reportlab(html_texto):
    """Convierte y limpia etiquetas HTML para que ReportLab las procese sin errores de sintaxis."""
    if not html_texto:
        return ["&nbsp;"]
    
    # 1. Asegurar que los saltos de línea y etiquetas br usen el formato XML correcto <br/>
    texto = html_texto.replace('<br>', '<br/>').replace('</br>', '')
    texto = texto.replace('</p>', '<br/><br/>').replace('<p>', '')
    
    # 2. Reemplazar etiquetas comunes por equivalentes de ReportLab
    texto = texto.replace('<strong>', '<b>').replace('</strong>', '</b>')
    texto = texto.replace('<em>', '<i>').replace('</em>', '</i>')
    texto = texto.replace('<ul>', '').replace('</ul>', '')
    texto = texto.replace('<li>', '• ').replace('</li>', '<br/>')
    
    # 3. Limpiar caracteres especiales conflictivos de XML pero manteniendo las etiquetas permitidas
    # ReportLab acepta <b>, <i>, <u>, <br/>
    lineas = texto.split('<br/>')
    parrafos_finales = []
    
    for l in lineas:
        l_limpia = l.strip()
        if l_limpia:
            parrafos_finales.append(l_limpia)
        else:
            parrafos_finales.append("&nbsp;")
            
    return parrafos_finales


def generar_pdf_oficio(ruta_pdf, folio, asunto, texto_cuerpo):
    """Compila el documento PDF aplicando el membrete, folio, asunto y cuerpo enriquecido."""
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        rightMargin=54,   
        leftMargin=54,    
        topMargin=230,    
        bottomMargin=110  
    )
    
    styles = getSampleStyleSheet()
    
    estilo_parrafo = ParagraphStyle(
        'EstiloOficio',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,           
        alignment=TA_JUSTIFY, 
        spaceAfter=10         
    )

    story = []
    
    lineas_procesadas = limpiar_html_para_reportlab(texto_cuerpo)
    for linea in lineas_procesadas:
        story.append(Paragraph(linea, estilo_parrafo))
    
    def on_first_page(canvas, doc):
        dibujar_fondo_membrete(canvas, doc)
        canvas.saveState()
        
        # Folio en la parte superior izquierda
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(54, 645, f"Oficio No. {folio}")
        
        # Asunto en la parte superior izquierda
        canvas.setFont("Helvetica", 10)
        canvas.drawString(54, 630, f"Asunto: {asunto}")
        
        canvas.restoreState()

    def on_later_pages(canvas, doc):
        dibujar_fondo_membrete(canvas, doc)

    doc.build(
        story, 
        onFirstPage=on_first_page, 
        onLaterPages=on_later_pages
    )