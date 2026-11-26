import unittest
from unittest.mock import patch

from views.applogin import _autenticar


class LoginAuthenticationTests(unittest.TestCase):
    def test_authentication_failure_is_returned_for_ui_reporting(self):
        error = RuntimeError('Microsoft client is not configured.')
        with patch('views.applogin.iniciar_sesion_interactivo',
                   side_effect=error):
            result, actual_error = _autenticar()

        self.assertIsNone(result)
        self.assertIs(actual_error, error)

    def test_authentication_result_is_returned_without_error(self):
        result = {'access_token': 'token'}
        with patch('views.applogin.iniciar_sesion_interactivo',
                   return_value=result):
            actual_result, error = _autenticar()

        self.assertIs(actual_result, result)
        self.assertIsNone(error)


if __name__ == '__main__':
    unittest.main()
