import types
import unittest
from unittest.mock import MagicMock, patch

from views.ui_helpers import Shell


class NotificacionesIntegradasTests(unittest.TestCase):
    def test_contador_rojo_combina_avisos_y_borradores(self):
        pantalla = types.SimpleNamespace(
            notification_button=MagicMock(), notification_badge=MagicMock())
        Shell._mostrar_contador_notificaciones(pantalla, 1, 2)
        pantalla.notification_badge.configure.assert_called_with(text='3')
        pantalla.notification_badge.place.assert_called_once()
        Shell._mostrar_contador_notificaciones(pantalla, 0, 0)
        pantalla.notification_badge.place_forget.assert_called_once()

    @patch('views.ui_helpers.open_screen')
    @patch('model.document_store.registrar_folio_local')
    @patch('controller.database_conecction.Database_connection')
    def test_seguir_editando_usa_borrador_postgresql(self, db, registrar, navegar):
        db.return_value.obtener_borrador.return_value = {
            'folio': 'IPN/CVDRD/059/2026', 'estado': 'Borrador'
        }
        ventana = MagicMock()
        pantalla = types.SimpleNamespace(usuario_id='usuario',
                                          actualizar_contador_notificaciones=MagicMock())
        Shell._abrir_borrador_desde_notificacion(
            pantalla, ventana, 'IPN/CVDRD/059/2026', 'Borrador')
        registrar.assert_called_once_with('IPN/CVDRD/059/2026')
        navegar.assert_called_once_with(pantalla, 'crear_documento.py', 'IPN/CVDRD/059/2026')
        ventana.destroy.assert_called_once()

    @patch('views.ui_helpers.open_screen')
    @patch('model.document_store.registrar_folio_local')
    @patch('controller.database_conecction.Database_connection')
    def test_guardar_reutiliza_metodo_del_editor_de_companero(self, db, registrar, navegar):
        folio = 'IPN/CVDRD/059/2026'
        db.return_value.obtener_borrador.return_value = {'folio': folio, 'estado': 'Borrador'}
        pagina = MagicMock(folio=folio)
        pantalla = types.SimpleNamespace(usuario_id='usuario',
            winfo_toplevel=lambda: types.SimpleNamespace(active_page=pagina),
            actualizar_contador_notificaciones=MagicMock())
        Shell._abrir_borrador_desde_notificacion(pantalla, MagicMock(), folio, 'Borrador', guardar=True)
        pagina.guardar.assert_called_once()


if __name__ == '__main__':
    unittest.main()
