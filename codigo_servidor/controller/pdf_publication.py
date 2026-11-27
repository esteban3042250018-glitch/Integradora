"""Generate and publish the final PDF for a saved document."""
from controller.database_conecction import Database_connection
from controller.pdf_generator import generar_pdf_oficio
from controller.sftp_storage import upload_file_to_server
from model.document_store import ruta_pdf_oficio


def publicar_pdf_oficio(folio, registro, usuario_id):
    destino = ruta_pdf_oficio(folio)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        generar_pdf_oficio(
            str(destino),
            folio,
            registro.get('asunto', ''),
            registro.get('cuerpo', ''),
            registro.get('area_emisora', ''),
            registro.get('recepcion', ''),
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise RuntimeError(f'No se pudo generar el PDF local: {error}') from error

    try:
        ruta_servidor = upload_file_to_server(destino)
    except (OSError, RuntimeError, ValueError) as error:
        raise RuntimeError(
            f'El PDF se generó localmente, pero no se subió al servidor: {error}'
        ) from error

    try:
        Database_connection().registrar_pdf_generado(
            folio,
            registro.get('asunto', ''),
            ruta_servidor,
            usuario_id,
            registro.get('area_emisora', ''),
        )
    except (ConnectionError, RuntimeError, ValueError) as error:
        raise RuntimeError(
            f'El PDF se subió al servidor ({ruta_servidor}), pero no se pudo '
            f'guardar su ruta en PostgreSQL: {error}'
        ) from error

    return ruta_servidor
