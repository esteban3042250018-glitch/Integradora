import unittest

from model.search_filters import matching_records


RECORDS = [
    ("REC-1048", "RECIBIDA", "Solicitud ampliación presupuestal", "Finanzas",
     "Dirección Administrativa", "Alta", "AR", "A. Ríos", "Por asignar", "2026-11-04"),
    ("REC-1047", "RECIBIDA", "Invitación Comité Técnico", "Jurídica",
     "Secretaría Particular", "Media", "MD", "M. Díaz", "En atención", "2026-11-05"),
    ("ENV-0831", "ENVIADA", "Respuesta oficio DGA/229/2026", "Dirección General",
     "Órgano Interno de Control", "Normal", "LS", "L. Soto", "Respondida", "2026-11-06"),
    ("REC-1046", "RECIBIDA", "Actualización padrón proveedores", "Recursos Materiales",
     "Adquisiciones", "Media", "JL", "J. León", "Turnada", "2026-11-07"),
]


class SearchFiltersTests(unittest.TestCase):
    def test_search_is_case_insensitive_and_matches_all_terms(self):
        result = matching_records(RECORDS, query="SOLICITUD PRESUPUESTAL")
        self.assertEqual([row[0] for row in result], ["REC-1048"])

    def test_state_and_priority_can_be_combined(self):
        result = matching_records(RECORDS, state="En atención", priority="Media")
        self.assertEqual([row[0] for row in result], ["REC-1047"])

    def test_category_filters_sent_items(self):
        result = matching_records(RECORDS, category="enviada")
        self.assertEqual([row[0] for row in result], ["ENV-0831"])

    def test_category_filters_follow_up_states(self):
        result = matching_records(RECORDS, category="seguimiento")
        self.assertEqual([row[0] for row in result], ["REC-1047", "REC-1046"])

    def test_category_filters_records_with_folio(self):
        result = matching_records(RECORDS, category="con_folio")
        self.assertEqual(len(result), 4)

    def test_short_or_malformed_records_are_skipped(self):
        result = matching_records([("folio", "RECIBIDA"), *RECORDS])
        self.assertEqual(len(result), 4)


if __name__ == "__main__":
    unittest.main()
