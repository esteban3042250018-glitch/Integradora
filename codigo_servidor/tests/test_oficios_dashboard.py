import unittest
from unittest.mock import MagicMock, patch

from model.oficios import (
    filtrar_oficios, listar_oficios_area, listar_oficios_dashboard,
    marcar_aprobado, resumir_estados,
)
from views.oficios_ui import _copiar_adjunto


class OficiosDashboardTests(unittest.TestCase):
    def test_summary_counts_common_missing_and_additional_states(self):
        resumen = resumir_estados([
            {'estado': 'Enviado'},
            {'estado': 'Enviado'},
            {'estado': None},
            {'estado': 'En revisión'},
        ])

        self.assertEqual(
            {item['estado']: item['total'] for item in resumen},
            {
                'Registrado': 0, 'Creado': 0, 'Enviado': 2,
                'Aprobado': 0, 'Acusado': 0, 'Sin estado': 1,
                'En revisión': 1,
            },
        )
        self.assertEqual(
            {item['estado']: item['porcentaje'] for item in resumen},
            {
                'Registrado': 0, 'Creado': 0, 'Enviado': 50.0,
                'Aprobado': 0, 'Acusado': 0, 'Sin estado': 25.0,
                'En revisión': 25.0,
            },
        )

    def test_filters_by_status_area_and_search_text(self):
        registros = [
            {
                'folio': 'IPN/001', 'asunto': 'Compra de equipo',
                'area': 'Informática', 'estado': 'Enviado',
            },
            {
                'folio': 'IPN/002', 'asunto': 'Mantenimiento',
                'area': 'Informática', 'estado': 'Creado',
            },
            {
                'folio': 'IPN/003', 'asunto': 'Compra de equipo',
                'area': 'Finanzas', 'estado': 'Enviado',
            },
        ]

        self.assertEqual(
            filtrar_oficios(
                registros, estado='enviado', area='informática',
                consulta='COMPRA',
            ),
            [registros[0]],
        )
        self.assertEqual(filtrar_oficios(registros), registros)

    @patch('model.oficios.Database_connection')
    def test_dashboard_query_uses_the_shared_database(self, database):
        database.return_value.ejecutar_consulta.return_value = [
            {'folio': 'IPN/001', 'id_oficio': 1},
        ]

        self.assertEqual(
            listar_oficios_dashboard(),
            [{'folio': 'IPN/001', 'id_oficio': 1, 'puede_gestionar': False}],
        )
        query = database.return_value.ejecutar_consulta.call_args.args[0]
        self.assertIn('correspondencia.oficios_estatus', query)
        self.assertIn("historial.activo = TRUE", query)
        self.assertIn("LIMIT 1", query)

    @patch('model.oficios.listar_oficios_area', return_value=[{'id_oficio': 1}])
    @patch('model.oficios.Database_connection')
    def test_dashboard_marks_offices_assigned_to_the_current_user(
        self, database, listar_area,
    ):
        database.return_value.ejecutar_consulta.return_value = [
            {'id_oficio': 1}, {'id_oficio': 2},
        ]

        registros = listar_oficios_dashboard('persona@example.org')

        self.assertEqual(
            [registro['puede_gestionar'] for registro in registros],
            [True, False],
        )
        listar_area.assert_called_once_with('persona@example.org')

    @patch('model.oficios.Database_connection')
    def test_area_list_supports_offices_linked_from_the_saved_draft(self, database):
        listar_oficios_area('persona@example.org')

        query = database.return_value.ejecutar_consulta.call_args.args[0]
        self.assertIn('correspondencia.borradores', query)
        self.assertIn('correspondencia.area_empleado', query)
        self.assertEqual(
            database.return_value.ejecutar_consulta.call_args.args[1],
            ('persona@example.org',),
        )

    @patch('model.oficios.Database_connection')
    def test_approval_updates_state_only_after_area_authorization(self, database):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [(True,), (4,)]
        database.return_value.get_connection.return_value = connection

        marcar_aprobado(
            7, '/srv/oficios/Aprobado_IPN_001.pdf', 'persona@example.org')

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any('INSERT INTO correspondencia.aprobados' in q for q in statements))
        self.assertTrue(any('INSERT INTO correspondencia.oficios_estatus' in q for q in statements))
        connection.commit.assert_called_once()

    @patch('model.oficios.Database_connection')
    def test_approval_rejects_users_outside_the_office_area(self, database):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = (False,)
        database.return_value.get_connection.return_value = connection

        with self.assertRaises(PermissionError):
            marcar_aprobado(
                7, '/srv/oficios/Aprobado_IPN_001.pdf',
                'otra.persona@example.org')

        cursor.execute.assert_called_once()
        connection.rollback.assert_called_once()

    @patch(
        'views.oficios_ui.upload_adjunto_oficio',
        return_value='/srv/oficios/Aprobado_IPN_001.pdf',
    )
    def test_dashboard_uploads_attachment_using_the_office_folio(
        self, upload_attachment,
    ):
        registro = {'folio': 'IPN/CVDRD/001/2026'}

        ruta = _copiar_adjunto(
            registro, 'Aprobado', 'C:\\documentos\\aprobacion.pdf')

        self.assertEqual(ruta, '/srv/oficios/Aprobado_IPN_001.pdf')
        upload_attachment.assert_called_once_with(
            'C:\\documentos\\aprobacion.pdf',
            'IPN/CVDRD/001/2026',
            'Aprobado',
        )


if __name__ == '__main__':
    unittest.main()
