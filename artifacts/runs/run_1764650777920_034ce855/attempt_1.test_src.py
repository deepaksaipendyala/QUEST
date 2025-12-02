import unittest
from unittest.mock import Mock, patch
from django.core.exceptions import FieldError
from django.db.models.query_utils import Q, select_related_descend, FilteredRelation, check_rel_lookup_compatibility

class QueryUtilsTests(unittest.TestCase):

    def test_q_combination_and(self):
        q1 = Q(foo='bar')
        q2 = Q(baz='qux')
        combined = q1 & q2
        self.assertEqual(combined.connector, Q.AND)
        self.assertEqual(len(combined.children), 2)
        self.assertIn(('foo', 'bar'), combined.children)
        self.assertIn(('baz', 'qux'), combined.children)

    def test_q_combination_or(self):
        q1 = Q(foo='bar')
        q2 = Q(baz='qux')
        combined = q1 | q2
        self.assertEqual(combined.connector, Q.OR)
        self.assertEqual(len(combined.children), 2)
        self.assertIn(('foo', 'bar'), combined.children)
        self.assertIn(('baz', 'qux'), combined.children)

    def test_q_negation(self):
        q = Q(foo='bar')
        negated = ~q
        self.assertTrue(negated.negated)
        self.assertEqual(len(negated.children), 1)
        self.assertIn(('foo', 'bar'), negated.children)

    def test_deconstruct_q(self):
        q = Q(foo='bar', baz='qux', _connector=Q.OR, _negated=True)
        path, args, kwargs = q.deconstruct()
        self.assertIn('django.db.models.query_utils.Q', path)
        self.assertEqual(args, (('foo', 'bar'), ('baz', 'qux')))
        self.assertEqual(kwargs, {'_connector': Q.OR, '_negated': True})

    def test_deferred_attribute_get(self):
        mock_field = Mock()
        mock_field.attname = 'mock_field'
        instance = Mock()
        instance.__dict__ = {}
        deferred = DeferredAttribute(mock_field)

        with patch.object(instance, 'refresh_from_db') as mock_refresh:
            value = deferred.__get__(instance)
            self.assertIsNone(value)
            mock_refresh.assert_called_once_with(fields=['mock_field'])

    def test_select_related_descend(self):
        mock_field = Mock()
        mock_field.remote_field = True
        mock_field.name = 'related_field'
        mock_field.null = False
        requested = {'related_field': True}
        load_fields = {'related_field'}
        result = select_related_descend(mock_field, False, requested, load_fields)
        self.assertTrue(result)

        # Test with no requested fields
        requested_empty = {}
        result_empty = select_related_descend(mock_field, False, requested_empty, load_fields)
        self.assertFalse(result_empty)

    def test_check_rel_lookup_compatibility(self):
        model = Mock()
        target_opts = Mock()
        field = Mock()
        model._meta.concrete_model = 'ModelA'
        target_opts.concrete_model = 'ModelA'
        field.primary_key = False

        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))

        # Test with different models
        target_opts.concrete_model = 'ModelB'
        self.assertFalse(check_rel_lookup_compatibility(model, target_opts, field))

    def test_filtered_relation_initialization(self):
        with self.assertRaises(ValueError):
            FilteredRelation('', condition=Q())

    def test_filtered_relation_condition_type(self):
        with self.assertRaises(ValueError):
            FilteredRelation('relation_name', condition='not_a_q_instance')

    def test_filtered_relation_equality(self):
        fr1 = FilteredRelation('relation_name', condition=Q(foo='bar'))
        fr2 = FilteredRelation('relation_name', condition=Q(foo='bar'))
        self.assertEqual(fr1, fr2)
        self.assertIsNot(fr1, fr2)

        fr3 = FilteredRelation('relation_name', condition=Q(foo='baz'))
        self.assertNotEqual(fr1, fr3)

    def test_filtered_relation_clone(self):
        fr = FilteredRelation('relation_name', condition=Q(foo='bar'))
        clone = fr.clone()
        self.assertEqual(fr, clone)
        self.assertIsNot(fr, clone)

    def test_filtered_relation_invalid_condition(self):
        with self.assertRaises(ValueError):
            FilteredRelation('relation_name', condition=None)

    def test_filtered_relation_with_empty_condition(self):
        fr = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(fr.condition, Q())

    def test_filtered_relation_with_multiple_conditions(self):
        fr1 = FilteredRelation('relation_name', condition=Q(foo='bar') & Q(baz='qux'))
        fr2 = FilteredRelation('relation_name', condition=Q(foo='bar') & Q(baz='qux'))
        self.assertEqual(fr1, fr2)

    def test_filtered_relation_with_different_conditions(self):
        fr1 = FilteredRelation('relation_name', condition=Q(foo='bar'))
        fr2 = FilteredRelation('relation_name', condition=Q(baz='qux'))
        self.assertNotEqual(fr1, fr2)

    def test_q_combination_and_empty(self):
        q1 = Q()
        q2 = Q(baz='qux')
        combined = q1 & q2
        self.assertEqual(combined, q2)

    def test_q_combination_or_empty(self):
        q1 = Q()
        q2 = Q(baz='qux')
        combined = q1 | q2
        self.assertEqual(combined, q2)

    def test_q_negation_empty(self):
        q = Q()
        negated = ~q
        self.assertTrue(negated.negated)
        self.assertEqual(len(negated.children), 0)

    def test_deconstruct_q_empty(self):
        q = Q()
        path, args, kwargs = q.deconstruct()
        self.assertIn('django.db.models.query_utils.Q', path)
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

    def test_select_related_descend_with_none(self):
        mock_field = Mock()
        mock_field.remote_field = True
        mock_field.name = 'related_field'
        mock_field.null = True
        requested = {'related_field': None}
        load_fields = {'related_field'}
        result = select_related_descend(mock_field, False, requested, load_fields)
        self.assertFalse(result)

    def test_check_rel_lookup_compatibility_primary_key(self):
        model = Mock()
        target_opts = Mock()
        field = Mock()
        model._meta.concrete_model = 'ModelA'
        target_opts.concrete_model = 'ModelA'
        field.primary_key = True

        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))

    def test_check_rel_lookup_compatibility_different_primary_key(self):
        model = Mock()
        target_opts = Mock()
        field = Mock()
        model._meta.concrete_model = 'ModelA'
        target_opts.concrete_model = 'ModelA'
        field.primary_key = False

        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))

        target_opts.concrete_model = 'ModelB'
        self.assertFalse(check_rel_lookup_compatibility(model, target_opts, field))