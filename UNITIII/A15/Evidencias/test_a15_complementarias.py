"""Pruebas complementarias elaboradas para el cierre A15.

Todas las pruebas usan dobles de interfaz/base de datos; no conectan con
PostgreSQL, Microsoft Entra ni SFTP reales.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from model.oficios import marcar_acusado, obtener_historial_estados
from views.crear_documento import CrearDocumentoApp


class A15Complementarias(unittest.TestCase):
    def test_captura_rechaza_cada_campo_obligatorio_vacio(self):
        casos = [
            ('asunto', '', 'Completa el campo Asunto.'),
            ('area_emisora', '', 'Selecciona un Área emisora.'),
            ('area_emisora', 'Selecciona un área', 'Selecciona un Área emisora.'),
            ('recepcion', '', 'Completa el campo Recepción.'),
        ]
        for campo, valor, mensaje in casos:
            with self.subTest(campo=campo, valor=valor):
                valores = {
                    'asunto': 'Asunto válido',
                    'area_emisora': 'Dirección',
                    'recepcion': 'Área destinataria',
                }
                valores[campo] = valor
                controles = {
                    nombre: SimpleNamespace(get=lambda v=v: v, focus_set=Mock())
                    for nombre, v in valores.items()
                }
                app = SimpleNamespace(**controles, cuerpo_html='<p>Texto</p>')
                app.advertir = Mock()
                CrearDocumentoApp.guardar(app)
                app.advertir.assert_called_once_with(mensaje, getattr(app, campo))

    @patch('model.oficios.Database_connection')
    def test_acuse_con_comentario_se_registra_y_actualiza_estado(self, database):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [(True,), (4,)]
        database.return_value.get_connection.return_value = connection
        marcar_acusado(7, 'usuario@example.org', comentario='Recibido en ventanilla')
        sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any('INSERT INTO correspondencia.acuses' in q for q in sql))
        self.assertTrue(any('INSERT INTO correspondencia.oficios_estatus' in q for q in sql))
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

    @patch('model.oficios.Database_connection')
    def test_acuse_sin_archivo_ni_comentario_revierte_transaccion(self, database):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [(True,), (4,)]
        database.return_value.get_connection.return_value = connection
        with self.assertRaisesRegex(ValueError, 'Adjunta un archivo o escribe un comentario'):
            marcar_acusado(7, 'usuario@example.org')
        sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any('INSERT INTO correspondencia.acuses' in q for q in sql))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()

    @patch('model.oficios.Database_connection')
    def test_historial_consulta_orden_cronologico_descendente(self, database):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.description = [('estado',), ('fecha_modificacion',), ('activo',)]
        cursor.fetchall.return_value = [('Enviado', '2026-11-27T10:00:00', True)]
        database.return_value.get_connection.return_value = connection
        resultado = obtener_historial_estados(7)
        self.assertEqual(resultado[0]['estado'], 'Enviado')
        sql = cursor.execute.call_args.args[0]
        self.assertIn('ORDER BY oe.fecha_modificacion DESC', sql)
        self.assertIn('oe.id_oficio_estatus DESC', sql)
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()