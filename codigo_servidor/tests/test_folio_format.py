from datetime import date
import unittest
from unittest.mock import MagicMock, patch

from model.folio_format import (
    build_configuration,
    configuration_from_row,
    editor_segments_from_configuration,
    render_folio,
    reserve_next_folio,
    _siguiente_numero,
    _folios_existentes,
    template_from_editor_segments,
)


class FolioFormatTests(unittest.TestCase):
    def test_existing_folio_lookup_uses_tables_in_current_schema(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [('IPN-001-2026',), ('IPN-002-2026',)]

        folios = _folios_existentes(cursor)

        self.assertEqual(folios, {'IPN-001-2026', 'IPN-002-2026'})
        query = cursor.execute.call_args.args[0]
        self.assertIn('correspondencia.oficios_envio', query)
        self.assertIn('correspondencia.borradores', query)
        self.assertNotIn('oficios_recibido', query)

    def test_default_format_uses_hyphen_between_blocks(self):
        configuration = build_configuration(
            'IPN/CVDRD/{numero}/{ano}', 3, 'Arial', 10)

        self.assertEqual(
            render_folio(7, configuration, year=2026),
            'IPN-CVDRD-007-2026',
        )

    def test_custom_format_and_style_are_validated(self):
        configuration = build_configuration(
            'DG/{numero}-OF/{ano}', '5', 'Times New Roman', '12.5')

        self.assertEqual(
            render_folio(23, configuration, year=2026),
            'DG-00023-OF-2026',
        )
        self.assertEqual(configuration['fuente'], 'Times New Roman')
        self.assertEqual(configuration['tamano'], 12.5)

    def test_custom_separator_and_order_are_rendered(self):
        segments = [
            {'tipo': 'texto', 'valor': 'IPN-CVDRD-'},
            {'tipo': 'anio', 'valor': ''},
            {'tipo': 'texto', 'valor': '-'},
            {'tipo': 'numero', 'valor': ''},
        ]
        template = template_from_editor_segments(segments)
        configuration = build_configuration(template, 3, 'Arial', 10)

        self.assertEqual(
            render_folio(1, configuration, year=2026),
            'IPN-CVDRD-2026-001',
        )
        self.assertEqual(template.count('/'), 0)

    def test_persistent_year_override_is_used_for_folio_and_sequence(self):
        configuration = build_configuration(
            'IPN/CVDRD/{numero}/{ano}', 3, 'Arial', 10, '2027')
        self.assertEqual(
            render_folio(1, configuration),
            'IPN-CVDRD-001-2027',
        )

        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        self.assertEqual(
            _siguiente_numero(
                cursor,
                configuration,
                {'IPN/CVDRD/001/2026'},
            ),
            1,
        )

    @patch('model.folio_format._folios_existentes')
    @patch('model.folio_format.read_configuration')
    def test_reservation_after_reset_starts_at_one_for_new_year(
            self, read_configuration, existing_folios):
        configuration = build_configuration(
            'IPN/CVDRD/{numero}/{ano}', 3, 'Arial', 10, 2027)
        read_configuration.return_value = configuration
        existing_folios.return_value = {
            'IPN/CVDRD/001/2026',
            'IPN/CVDRD/002/2026',
        }
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)

        folio = reserve_next_folio(cursor)

        self.assertEqual(folio, 'IPN-CVDRD-001-2027')
        self.assertEqual(
            render_folio(1, configuration), 'IPN-CVDRD-001-2027')
        self.assertEqual(cursor.execute.call_args_list[-1].args[1], (2,))

    def test_configuration_row_reads_persisted_year(self):
        configuration = configuration_from_row((
            [
                {'tipo': 'texto', 'valor': 'IPN/'},
                {'tipo': 'numero', 'valor': '/'},
                {'tipo': 'anio', 'valor': ''},
            ],
            3,
            'Arial',
            10,
            2027,
        ))

        self.assertEqual(configuration['anio_folio'], 2027)
        self.assertEqual(
            render_folio(4, configuration),
            'IPN-004-2027',
        )

    def test_year_block_accepts_separator_after_it(self):
        segments = [
            {'tipo': 'texto', 'valor': 'IPN-CVDRD-'},
            {'tipo': 'anio', 'valor': '/'},
            {'tipo': 'numero', 'valor': ''},
        ]
        template = template_from_editor_segments(segments)
        configuration = build_configuration(template, 3, 'Arial', 10)

        self.assertEqual(
            render_folio(1, configuration, year=2026),
            'IPN-CVDRD-2026-001',
        )
        reloaded_segments = editor_segments_from_configuration(configuration)
        self.assertEqual(
            template_from_editor_segments(reloaded_segments),
            template,
        )

    def test_format_uses_editable_blocks_and_roundtrips(self):
        segments = [
            {'tipo': 'texto', 'valor': 'IPN/CVDRD/'},
            {'tipo': 'numero', 'valor': ''},
            {'tipo': 'texto', 'valor': '/'},
            {'tipo': 'anio', 'valor': ''},
        ]
        template = template_from_editor_segments(segments)
        configuration = build_configuration(template, 3, 'Arial', 10)

        self.assertEqual(template, 'IPN-CVDRD-{numero}-{ano}')
        self.assertEqual(template_from_editor_segments(
            editor_segments_from_configuration(configuration)), template)
        self.assertEqual(
            render_folio(1, configuration, year=2026),
            'IPN-CVDRD-001-2026',
        )

    def test_added_segment_is_separated_with_a_hyphen(self):
        segments = [
            {'tipo': 'texto', 'valor': 'IPN'},
            {'tipo': 'texto', 'valor': 'CVDRD'},
            {'tipo': 'numero', 'valor': ''},
            {'tipo': 'anio', 'valor': ''},
            {'tipo': 'texto', 'valor': 'EXT'},
        ]

        template = template_from_editor_segments(segments)
        configuration = build_configuration(template, 3, 'Arial', 10)

        self.assertEqual(template, 'IPN-CVDRD-{numero}-{ano}-EXT')
        self.assertEqual(
            render_folio(1, configuration, year=2026),
            'IPN-CVDRD-001-2026-EXT',
        )

    def test_legacy_year_text_segment_is_a_year_block(self):
        configuration = configuration_from_row((
            [
                {'tipo': 'texto', 'valor': 'IPN/'},
                {'tipo': 'numero', 'valor': ''},
                {'tipo': 'texto', 'valor': '/'},
                {'tipo': 'texto', 'valor': 'AÑO'},
            ],
            3,
            'Arial',
            10,
        ))
        self.assertEqual(
            render_folio(4, configuration, year=2026),
            'IPN-004-2026',
        )

    def test_existing_slash_folios_match_the_new_hyphen_format(self):
        configuration = build_configuration(
            'IPN/CVDRD/{numero}/{ano}', 3, 'Arial', 10)

        self.assertEqual(
            _siguiente_numero(
                MagicMock(fetchone=MagicMock(return_value=(1,))),
                configuration,
                {'IPN/CVDRD/007/2026'},
            ),
            8,
        )

    def test_rejects_missing_or_repeated_number_token(self):
        for template in ('IPN/2026', '{numero}/{numero}'):
            with self.subTest(template=template):
                with self.assertRaises(ValueError):
                    build_configuration(template, 3, 'Arial', 10)

    @patch('model.folio_format._folios_existentes')
    @patch('model.folio_format.read_configuration')
    def test_reservation_uses_configured_counter_and_skips_used_folios(
            self, read_configuration, existing_folios):
        configuration = build_configuration(
            'IPN/CVDRD/{numero}/{ano}', 3, 'Arial', 10)
        read_configuration.return_value = configuration
        existing_folios.return_value = {
            f'IPN/CVDRD/015/{date.today().year}',
        }
        cursor = MagicMock()
        cursor.fetchone.return_value = (12,)

        folio = reserve_next_folio(cursor)

        self.assertEqual(
            folio, f'IPN-CVDRD-016-{date.today().year}')
        self.assertIn(
            'LOCK TABLE personalizacion.configuracion_folios',
            cursor.execute.call_args_list[0].args[0],
        )
        self.assertIn(
            'INSERT INTO personalizacion.configuracion_folios',
            cursor.execute.call_args_list[-1].args[0],
        )
        self.assertTrue(all(
            'correspondencia.folios_anuales' not in call.args[0]
            for call in cursor.execute.call_args_list
        ))


if __name__ == '__main__':
    unittest.main()
