import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from views.crear_documento import CrearDocumentoApp


class CreateDocumentSaveTests(unittest.TestCase):
    @patch('views.crear_documento.open_screen')
    @patch('views.crear_documento.messagebox.showinfo')
    @patch(
        'views.crear_documento.publicar_pdf_oficio',
        return_value='/srv/oficios/Oficio_001.pdf',
    )
    @patch('views.crear_documento.Database_connection')
    def test_success_message_uses_reserved_folio(
        self, database_connection, _publicar_pdf, showinfo, _open_screen,
    ):
        app = SimpleNamespace(
            folio='IPN/CVDRD/001/2026',
            asunto=SimpleNamespace(get=lambda: 'Asunto'),
            area_emisora=SimpleNamespace(get=lambda: 'Dirección'),
            recepcion=SimpleNamespace(get=lambda: 'Destinatario'),
            cuerpo_html='<p>Texto</p>',
            word_opened=False,
            word_synced=False,
            word_path=None,
            usuario_id='user-1',
            _autosave_job=None,
            estado=MagicMock(),
        )

        CrearDocumentoApp.guardar(app)

        database_connection.return_value.finalizar_borrador.assert_called_once()
        self.assertIn(
            app.folio,
            showinfo.call_args.args[1],
        )


if __name__ == '__main__':
    unittest.main()
