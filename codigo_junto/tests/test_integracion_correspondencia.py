import types
import unittest
from unittest.mock import Mock, patch

from model.microsoft_mail import (
    _clave_folio, _inbox_url, _mensajes_con_folio, obtener_correos_graph,
)
from model.folio import extraer_folio


class CorrespondenciaIntegradaTests(unittest.TestCase):
    def test_detecta_folios_reales_y_omite_mensajes_sin_folio(self):
        self.assertEqual(extraer_folio('Oficio IPN/cvdrd/070/2026'), 'IPN/cvdrd/070/2026')
        self.assertIsNone(extraer_folio('Hola, buen día'))

    def test_normaliza_folios_equivalentes(self):
        self.assertEqual(_clave_folio('IPN/CVDRD/0050/2026'),
                         _clave_folio('IPN/cvdrd/050/2026'))

    def test_preserva_todos_los_correos_repetidos_y_orden(self):
        mensajes = [
            {'subject': 'IPN/cvdrd/050/2026', 'receivedDateTime': '2026-11-09T12:00:00Z'},
            {'subject': 'Sin folio', 'receivedDateTime': '2026-11-09T13:00:00Z'},
            {'subject': 'IPN/CVDRD/0050/2026', 'receivedDateTime': '2026-11-09T14:00:00Z'},
            {'subject': 'IPN/CVDRD/051/2026', 'receivedDateTime': '2026-11-09T15:00:00Z'},
        ]
        entradas = _mensajes_con_folio(mensajes)
        self.assertEqual(len(entradas), 3)
        self.assertEqual([item[2] for item in entradas], [1, 2, 2])

    @patch('model.microsoft_mail._obtener_mensajes')
    def test_mantiene_estado_independiente_por_correo(self, obtener):
        obtener.return_value = [
            {'subject': 'IPN/CVDRD/050/2026', 'isRead': False,
             'receivedDateTime': '2026-11-09T12:00:00Z',
             'from': {'emailAddress': {'name': 'Ana', 'address': 'ana@example.com'}}},
            {'subject': 'IPN/CVDRD/050/2026', 'isRead': True,
             'receivedDateTime': '2026-11-09T13:00:00Z',
             'from': {'emailAddress': {'name': 'Luis', 'address': 'luis@example.com'}}},
        ]
        registros = obtener_correos_graph('usuario@outlook.com')
        self.assertEqual(len(registros), 2)
        self.assertEqual([r[8] for r in registros], ['Recibido', 'Por asignar'])
        self.assertEqual([r[11] for r in registros], ['2', '2'])
        self.assertEqual([r[13] for r in registros],
                         ['luis@example.com', 'ana@example.com'])
        obtener.assert_called_once_with('usuario@outlook.com')

    @patch('model.microsoft_mail.CONFIG')
    def test_buzon_propio_o_compartido(self, config):
        config.return_value = ''
        self.assertIn('/me/mailFolders/inbox/messages', _inbox_url())
        config.return_value = 'cvdr@escuela.edu.mx'
        self.assertIn('/users/cvdr%40escuela.edu.mx/mailFolders/inbox/messages',
                      _inbox_url())


if __name__ == '__main__':
    unittest.main()
