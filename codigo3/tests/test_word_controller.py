import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from docx import Document
from docx.shared import Inches

from controller.word_controller import preparar_documento_word


def _png_1x1():
    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )


class WordControllerTests(unittest.TestCase):
    def test_new_desktop_document_includes_active_letterhead(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "oficio.docx"
            connection = MagicMock()
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchall.return_value = [
                ("membrete.png", "image/png", _png_1x1()),
            ]

            with (
                patch("controller.word_controller.obtener_conexion",
                      return_value=connection),
                patch("controller.word_controller.ruta_docx_oficio",
                      return_value=path),
            ):
                result = preparar_documento_word(
                    "IPN/CVDRD/1/2026", "Asunto", "<p>Texto inicial</p>")

            self.assertEqual(result, path)
            connection.close.assert_called_once()

            document = Document(path)
            section = document.sections[0]
            self.assertEqual(section.page_width, Inches(8.5))
            self.assertEqual(section.top_margin, Inches(230 / 72))
            self.assertEqual(
                section.header.paragraphs[0].text,
                "FOLIO: IPN/CVDRD/1/2026",
            )
            self.assertIn("Texto inicial", "\n".join(
                paragraph.text for paragraph in document.paragraphs))
            self.assertIn("<wp:anchor", section.header._element.xml)
            with ZipFile(path) as archive:
                self.assertTrue(any(
                    name.startswith("word/media/") for name in archive.namelist()
                ))


if __name__ == "__main__":
    unittest.main()
