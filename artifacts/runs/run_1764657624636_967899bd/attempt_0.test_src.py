from django.test import SimpleTestCase
from django.db.models import IntegerField, Field
from django.db.models.expressions import Value
from django.core.exceptions import EmptyResultSet
from django.db.models.sql.query import Query
from django.utils.datastructures import OrderedSet
import tempfile
import pathlib

class LookupTests(SimpleTestCase):

    def setUp(self):
        self.lhs = IntegerField()
        self.rhs = Value(10)

    def test_exact_lookup(self):
        lookup = Exact(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'exact')

    def test_iexact_lookup(self):
        lookup = IExact(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'iexact')

    def test_greater_than_lookup(self):
        lookup = GreaterThan(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'gt')

    def test_greater_than_or_equal_lookup(self):
        lookup = GreaterThanOrEqual(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'gte')

    def test_less_than_lookup(self):
        lookup = LessThan(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'lt')

    def test_less_than_or_equal_lookup(self):
        lookup = LessThanOrEqual(self.lhs, self.rhs)
        self.assertEqual(lookup.lookup_name, 'lte')

    def test_in_lookup_with_empty_rhs(self):
        lookup = In(self.lhs, [])
        with self.assertRaises(EmptyResultSet):
            lookup.process_rhs(None, None)

    def test_in_lookup_with_valid_rhs(self):
        lookup = In(self.lhs, [1, 2, 3])
        sql, params = lookup.as_sql(None, None)
        self.assertIn('IN', sql)

    def test_contains_lookup(self):
        lookup = Contains(self.lhs, 'test')
        sql, params = lookup.as_sql(None, None)
        self.assertIn('LIKE', sql)

    def test_startswith_lookup(self):
        lookup = StartsWith(self.lhs, 'test')
        sql, params = lookup.as_sql(None, None)
        self.assertIn('LIKE', sql)

    def test_endswith_lookup(self):
        lookup = EndsWith(self.lhs, 'test')
        sql, params = lookup.as_sql(None, None)
        self.assertIn('LIKE', sql)

    def test_isnull_lookup(self):
        lookup = IsNull(self.lhs, True)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('IS NULL', sql)

    def test_regex_lookup(self):
        lookup = Regex(self.lhs, r'\d+')
        sql, params = lookup.as_sql(None, None)
        self.assertIn('REGEXP', sql)

    def test_iregex_lookup(self):
        lookup = IRegex(self.lhs, r'\d+')
        sql, params = lookup.as_sql(None, None)
        self.assertIn('REGEXP', sql)

    def test_year_exact_lookup(self):
        lookup = YearExact(self.lhs, 2021)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('BETWEEN', sql)

    def test_year_gt_lookup(self):
        lookup = YearGt(self.lhs, 2021)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('>', sql)

    def test_year_gte_lookup(self):
        lookup = YearGte(self.lhs, 2021)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('>=', sql)

    def test_year_lt_lookup(self):
        lookup = YearLt(self.lhs, 2021)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('<', sql)

    def test_year_lte_lookup(self):
        lookup = YearLte(self.lhs, 2021)
        sql, params = lookup.as_sql(None, None)
        self.assertIn('<=', sql)

    def test_batch_process_rhs_with_iterable(self):
        lookup = FieldGetDbPrepValueIterableMixin()
        sqls, params = lookup.batch_process_rhs(None, None, rhs=[1, 2, 3])
        self.assertEqual(len(params), 3)

    def test_batch_process_rhs_with_non_iterable(self):
        lookup = FieldGetDbPrepValueIterableMixin()
        sqls, params = lookup.batch_process_rhs(None, None, rhs=1)
        self.assertEqual(len(params), 1)

    def test_process_rhs_with_query(self):
        query = Query()
        lookup = Exact(self.lhs, query)
        with self.assertRaises(ValueError):
            lookup.process_rhs(None, None)

    def test_process_rhs_with_valid_query(self):
        query = Query()
        query.add_fields(['pk'])
        lookup = Exact(self.lhs, query)
        sql, params = lookup.process_rhs(None, None)
        self.assertIn('SELECT', sql)

    def test_process_rhs_with_invalid_query(self):
        query = Query()
        lookup = Exact(self.lhs, query)
        with self.assertRaises(ValueError):
            lookup.process_rhs(None, None)

    def test_get_db_prep_lookup_with_iterable(self):
        lookup = FieldGetDbPrepValueIterableMixin()
        result = lookup.get_db_prep_lookup([1, 2, 3], None)
        self.assertEqual(len(result[1]), 3)

    def test_get_db_prep_lookup_with_non_iterable(self):
        lookup = FieldGetDbPrepValueMixin()
        result = lookup.get_db_prep_lookup(1, None)
        self.assertEqual(len(result[1]), 1)