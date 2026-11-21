import unittest
from datetime import date

from controller.correspondence_search import build_search_query


class CorrespondenceSearchQueryTests(unittest.TestCase):
    def test_combines_all_supported_filters_as_parameters(self):
        query, params = build_search_query(
            folio="CVDR/015",
            asunto="presupuesto",
            fecha_desde="2026-11-03",
            fecha_hasta="2026-11-13",
            departamento="Administrativa",
        )
        self.assertIn("UNION ALL", query)
        self.assertIn("folio ILIKE %s", query)
        self.assertIn("asunto ILIKE %s", query)
        self.assertIn("fecha >= %s", query)
        self.assertIn("fecha <= %s", query)
        self.assertIn("departamento ILIKE %s", query)
        self.assertEqual(
            params,
            ("%CVDR/015%", "%presupuesto%", "%Administrativa%",
             date(2026, 11, 3), date(2026, 11, 13)),
        )

    def test_user_text_is_never_interpolated_into_sql(self):
        injected = "' OR 1=1 --"
        query, params = build_search_query(folio=injected)
        self.assertNotIn(injected, query)
        self.assertEqual(params, (f"%{injected}%",))

    def test_empty_filters_return_complete_ordered_query(self):
        query, params = build_search_query()
        self.assertNotIn("\nWHERE ", query)
        self.assertIn("ORDER BY fecha DESC, folio ASC", query)
        self.assertEqual(params, ())

    def test_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(ValueError, "posterior"):
            build_search_query(fecha_desde="2026-11-14", fecha_hasta="2026-11-13")

    def test_rejects_invalid_date_format(self):
        with self.assertRaisesRegex(ValueError, "AAAA-MM-DD"):
            build_search_query(fecha_desde="13/11/2026")


if __name__ == "__main__":
    unittest.main()
