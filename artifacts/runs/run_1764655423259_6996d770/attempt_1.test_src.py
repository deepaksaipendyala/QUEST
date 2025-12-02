import unittest
from unittest.mock import Mock, patch
from django.core.exceptions import FieldError
from django.db.models.query_utils import Q, DeferredAttribute, select_related_descend, refs_expression, check_rel_lookup_compatibility, FilteredRelation

class QueryUtilsTests(unittest.TestCase):

    def test_q_combination(self):
        q1 = Q(name='John')
        q2 = Q(age=30)
        combined = q1 & q2
        self.assertIsInstance(combined, Q)
        self.assertEqual(combined.connector, Q.AND)

        combined_or = q1 | q2
        self.assertIsInstance(combined_or, Q)
        self.assertEqual(combined_or.connector, Q.OR)

        # Test empty Q objects
        empty_q = Q()
        combined_empty = empty_q & q1
        self.assertEqual(combined_empty, q1)

        combined_empty_or = empty_q | q1
        self.assertEqual(combined_empty_or, q1)

    def test_q_negation(self):
        q = Q(name='John')
        negated_q = ~q
        self.assertIsInstance(negated_q, Q)
        self.assertTrue(negated_q.negated)

        # Test double negation
        double_negated_q = ~~q
        self.assertEqual(double_negated_q, q)

    def test_deferred_attribute(self):
        mock_field = Mock()
        mock_field.attname = 'mock_field'
        instance = Mock()
        instance.__dict__ = {}
        deferred_attr = DeferredAttribute(mock_field)

        with patch.object(instance, 'refresh_from_db', return_value=None) as mock_refresh:
            value = deferred_attr.__get__(instance)
            self.assertIsNone(value)
            mock_refresh.assert_called_once_with(fields=['mock_field'])

        # Test setting the value
        deferred_attr.__set__(instance, 'new_value')
        self.assertEqual(instance.__dict__['mock_field'], 'new_value')

    def test_select_related_descend(self):
        mock_field = Mock()
        mock_field.remote_field = True
        mock_field.null = False
        mock_field.name = 'related_field'
        requested = {'related_field': True}
        load_fields = {'related_field'}

        result = select_related_descend(mock_field, False, requested, load_fields)
        self.assertTrue(result)

        # Test with restricted and reverse
        result = select_related_descend(mock_field, True, requested, load_fields, reverse=True)
        self.assertTrue(result)

        # Test with no requested fields
        result = select_related_descend(mock_field, False, {}, load_fields)
        self.assertFalse(result)

    def test_refs_expression(self):
        lookup_parts = ['field1', 'field2']
        annotations = {'field1': True, 'field1__field2': True}

        found, remaining = refs_expression(lookup_parts, annotations)
        self.assertTrue(found)
        self.assertEqual(remaining, ['field2'])

        # Test with no matches
        lookup_parts_no_match = ['field3']
        found, remaining = refs_expression(lookup_parts_no_match, annotations)
        self.assertFalse(found)
        self.assertEqual(remaining, ['field3'])

    def test_check_rel_lookup_compatibility(self):
        mock_model = Mock()
        mock_target_opts = Mock()
        mock_field = Mock()
        mock_model._meta.concrete_model = mock_model
        mock_target_opts.concrete_model = mock_target_opts

        result = check_rel_lookup_compatibility(mock_model, mock_target_opts, mock_field)
        self.assertTrue(result)

        # Test with incompatible models
        mock_target_opts.concrete_model = Mock()
        mock_target_opts.concrete_model._meta.model_name = 'different_model'
        result = check_rel_lookup_compatibility(mock_model, mock_target_opts, mock_field)
        self.assertFalse(result)

    def test_filtered_relation_initialization(self):
        with self.assertRaises(ValueError):
            FilteredRelation('', condition=Q())

        relation = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(relation.relation_name, 'relation_name')

    def test_filtered_relation_condition_type(self):
        with self.assertRaises(ValueError):
            FilteredRelation('relation_name', condition='not_a_q_instance')

        # Test with valid Q instance
        relation = FilteredRelation('relation_name', condition=Q(field='value'))
        self.assertEqual(relation.condition, Q(field='value'))

    def test_filtered_relation_equality(self):
        relation1 = FilteredRelation('relation_name', condition=Q())
        relation2 = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(relation1, relation2)

        # Test with different conditions
        relation3 = FilteredRelation('relation_name', condition=Q(field='value'))
        self.assertNotEqual(relation1, relation3)

    def test_filtered_relation_clone(self):
        relation = FilteredRelation('relation_name', condition=Q())
        clone = relation.clone()
        self.assertEqual(relation, clone)
        self.assertIsNot(relation, clone)

        # Test that the clone has the same attributes
        self.assertEqual(clone.relation_name, relation.relation_name)
        self.assertEqual(clone.condition, relation.condition)

    def test_filtered_relation_invalid_condition(self):
        with self.assertRaises(ValueError):
            FilteredRelation('relation_name', condition='invalid')

if __name__ == '__main__':
    unittest.main()