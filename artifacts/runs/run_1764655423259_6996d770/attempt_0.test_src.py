import tempfile
import unittest
from unittest.mock import Mock, patch
from django.core.exceptions import FieldError
from django.db.models.query_utils import Q, DeferredAttribute, select_related_descend, refs_expression, check_rel_lookup_compatibility, FilteredRelation

class QueryUtilsTests(unittest.TestCase):

    def test_q_combination(self):
        q1 = Q(name='John')
        q2 = Q(age=30)
        combined = q1 & q2
        self.assertTrue(isinstance(combined, Q))
        self.assertEqual(combined.connector, Q.AND)

        combined_or = q1 | q2
        self.assertTrue(isinstance(combined_or, Q))
        self.assertEqual(combined_or.connector, Q.OR)

    def test_q_negation(self):
        q = Q(name='John')
        negated_q = ~q
        self.assertTrue(isinstance(negated_q, Q))
        self.assertTrue(negated_q.negated)

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

    def test_refs_expression(self):
        lookup_parts = ['field1', 'field2']
        annotations = {'field1': True, 'field1__field2': True}
        
        found, remaining = refs_expression(lookup_parts, annotations)
        self.assertTrue(found)
        self.assertEqual(remaining, ['field2'])

    def test_check_rel_lookup_compatibility(self):
        mock_model = Mock()
        mock_target_opts = Mock()
        mock_field = Mock()
        mock_model._meta.concrete_model = mock_model
        mock_target_opts.concrete_model = mock_target_opts
        
        result = check_rel_lookup_compatibility(mock_model, mock_target_opts, mock_field)
        self.assertTrue(result)

    def test_filtered_relation_initialization(self):
        with self.assertRaises(ValueError):
            FilteredRelation('', condition=Q())

        relation = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(relation.relation_name, 'relation_name')

    def test_filtered_relation_condition_type(self):
        with self.assertRaises(ValueError):
            FilteredRelation('relation_name', condition='not_a_q_instance')

    def test_filtered_relation_equality(self):
        relation1 = FilteredRelation('relation_name', condition=Q())
        relation2 = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(relation1, relation2)

    def test_filtered_relation_clone(self):
        relation = FilteredRelation('relation_name', condition=Q())
        clone = relation.clone()
        self.assertEqual(relation, clone)
        self.assertIsNot(relation, clone)

if __name__ == '__main__':
    unittest.main()