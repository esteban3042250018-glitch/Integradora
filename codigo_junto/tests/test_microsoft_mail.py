import unittest
from unittest.mock import Mock, patch

from model.microsoft_mail import _mensajes_con_folio, obtener_correos_graph


class MicrosoftMailTests(unittest.TestCase):
    @patch('model.microsoft_mail.CONFIG')
    @patch('model.microsoft_mail.obtener_token_graph', return_value='token')
    @patch('model.microsoft_mail.requests.get')
    def test_does_not_fetch_subsequent_graph_pages(self, get, get_token, config):
        config.side_effect = lambda key, **kw: 2 if key == 'CVDR_MAX_MESSAGES' else kw.get('default', '')
        first_page = Mock(ok=True)
        first_page.json.return_value = {
            'value': [
                {'subject': 'IPN/CVDRD/050/2026', 'from': {'emailAddress': {'name': 'Ana'}},
                 'receivedDateTime': '2026-11-09T10:00:00Z', 'isRead': False},
                {'subject': 'IPN/CVDRD/051/2026', 'from': {'emailAddress': {'name': 'Luis'}},
                 'receivedDateTime': '2026-11-08T10:00:00Z', 'isRead': True},
            ],
            '@odata.nextLink': 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?page=2',
        }
        get.return_value = first_page

        records = obtener_correos_graph('user@example.com')
        self.assertEqual([record[0] for record in records],
                         ['IPN/CVDRD/050/2026', 'IPN/CVDRD/051/2026'])
        self.assertEqual([record[8] for record in records], ['Por asignar', 'Recibido'])
        get.assert_called_once()
        self.assertIn('/me/mailFolders/inbox/messages', get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs['timeout'], 30)
        get_token.assert_called_once_with('user@example.com')

    def test_repeated_folios_are_displayed_and_flagged(self):
        messages = [
            {'subject': 'IPN/CVDRD/050/2026', 'receivedDateTime': '2026-11-09T10:00:00Z'},
            {'subject': 'IPN/cvdrd/0050/2026', 'receivedDateTime': '2026-11-09T11:00:00Z'},
            {'subject': 'Correo personal', 'receivedDateTime': '2026-11-09T12:00:00Z'},
        ]
        results = _mensajes_con_folio(messages)
        self.assertEqual(len(results), 2)
        self.assertEqual([item[2] for item in results], [2, 2])


if __name__ == '__main__':
    unittest.main()
