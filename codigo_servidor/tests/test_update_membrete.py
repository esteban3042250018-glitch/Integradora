from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from views.update import COPY, REFUSE_DROP, DashboardApp


class LetterheadDropTests(unittest.TestCase):
    def test_preview_keeps_source_unchanged_and_does_not_apply_it(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'letterhead.png'
            Image.new('RGB', (20, 10), 'white').save(path, format='PNG')
            original = path.read_bytes()
            app = SimpleNamespace(
                preview=MagicMock(),
                details=MagicMock(),
                status=MagicMock(),
                apply_membrete_button=MagicMock(),
                cancel_membrete_button=MagicMock(),
                _pending_membrete_path=None,
                _imagen_preview=None,
            )

            with patch('views.update.ctk.CTkImage', return_value=object()), \
                    patch('views.update.cambiar_imagen_membrete') as apply:
                DashboardApp._previsualizar_membrete(app, str(path))

            self.assertEqual(app._pending_membrete_path, str(path))
            self.assertEqual(path.read_bytes(), original)
            apply.assert_not_called()
            app.apply_membrete_button.configure.assert_called_once_with(
                state='normal')

    def test_drop_accepts_one_file_and_rejects_multiple_files(self):
        app = SimpleNamespace(
            tk=SimpleNamespace(splitlist=lambda data: data.split('|')),
            _previsualizar_membrete=MagicMock(),
        )
        event = SimpleNamespace(data='C:/letterhead.png')

        self.assertEqual(
            DashboardApp._manejar_drop_membrete(app, event), COPY)
        app._previsualizar_membrete.assert_called_once_with(
            'C:/letterhead.png')

        event.data = 'C:/first.png|C:/second.png'
        with patch('views.update.messagebox.showwarning') as warning:
            self.assertEqual(
                DashboardApp._manejar_drop_membrete(app, event),
                REFUSE_DROP,
            )
        warning.assert_called_once()
        app._previsualizar_membrete.assert_called_once()

    def test_applying_requires_explicit_confirmation(self):
        path = 'C:/letterhead.png'
        app = SimpleNamespace(
            _pending_membrete_path=path,
            cargar_membrete=MagicMock(),
        )

        with patch('views.update.messagebox.askyesno', return_value=False), \
                patch('views.update.cambiar_imagen_membrete') as apply:
            DashboardApp.aplicar_membrete(app)
        apply.assert_not_called()

        with patch('views.update.messagebox.askyesno', return_value=True), \
                patch('views.update.cambiar_imagen_membrete') as apply, \
                patch('views.update.messagebox.showinfo'):
            DashboardApp.aplicar_membrete(app)
        apply.assert_called_once_with(path)
        app.cargar_membrete.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
