import unittest
from unittest.mock import Mock, patch

from model.microsoft_mail import GRAPH_MESSAGES_URL, obtener_correos_graph


class MicrosoftMailTests(unittest.TestCase):
    @patch("model.microsoft_mail.obtener_token_graph", return_value="token")
    @patch("model.microsoft_mail.requests.get")
    def test_does_not_fetch_subsequent_graph_pages(self, get, _get_token):
        first_message = {
            "subject": "Primer mensaje",
            "from": {"emailAddress": {"name": "Ana"}},
            "receivedDateTime": "2026-11-09T10:00:00Z",
        }
        second_message = {
            "subject": "Segundo mensaje",
            "from": {"emailAddress": {"name": "Luis"}},
            "receivedDateTime": "2026-11-08T10:00:00Z",
        }
        first_page = Mock(ok=True)
        first_page.json.return_value = {
            "value": [first_message, second_message],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?page=2",
        }
        get.return_value = first_page

        records = obtener_correos_graph("user@example.com")

        self.assertEqual(
            [record[2] for record in records],
            ["Primer mensaje", "Segundo mensaje"],
        )
        get.assert_called_once()
        self.assertEqual(get.call_args.args[0], GRAPH_MESSAGES_URL)
        self.assertEqual(get.call_args.kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
