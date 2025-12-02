import unittest
from django.core.exceptions import FieldError
from django.db.models.query_utils import Q, select_related_descend, FilteredRelation, check_rel_lookup_compatibility

class QueryUtilsTests(unittest.TestCase):

    def test_q_combination_and(self):
        q1 = Q(name='test')
        q2 = Q(age=30)
        combined = q1 & q2
        self.assertTrue(isinstance(combined, Q))
        self.assertEqual(combined.connector, Q.AND)
        self.assertEqual(combined.children, [('test',), (30,)])

    def test_q_combination_or(self):
        q1 = Q(name='test')
        q2 = Q(age=30)
        combined = q1 | q2
        self.assertTrue(isinstance(combined, Q))
        self.assertEqual(combined.connector, Q.OR)
        self.assertEqual(combined.children, [('test',), (30,)])

    def test_q_negation(self):
        q = Q(name='test')
        negated = ~q
        self.assertTrue(isinstance(negated, Q))
        self.assertTrue(negated.negated)
        self.assertEqual(negated.children, [('test',)])

    def test_deconstruct_q(self):
        q = Q(name='test', age=30)
        path, args, kwargs = q.deconstruct()
        self.assertIn('django.db.models.query_utils.Q', path)
        self.assertEqual(args, ('test', 30))
        self.assertEqual(kwargs, {})

    def test_select_related_descend(self):
        field = unittest.mock.Mock()
        field.remote_field = unittest.mock.Mock()
        field.remote_field.parent_link = False
        field.name = 'related_field'
        field.null = False

        self.assertTrue(select_related_descend(field, False, {'related_field': True}, set(), False))
        self.assertFalse(select_related_descend(field, True, {'other_field': True}, set(), False))
        self.assertFalse(select_related_descend(field, False, {'related_field': False}, set(), False))

    def test_filtered_relation_init(self):
        with self.assertRaises(ValueError):
            FilteredRelation('', condition=Q())

    def test_filtered_relation_condition(self):
        fr = FilteredRelation('relation_name', condition=Q(name='test'))
        self.assertEqual(fr.relation_name, 'relation_name')
        self.assertEqual(fr.condition, Q(name='test'))
        self.assertIsInstance(fr.condition, Q)

    def test_check_rel_lookup_compatibility(self):
        model = unittest.mock.Mock()
        target_opts = unittest.mock.Mock()
        field = unittest.mock.Mock()
        field.primary_key = False

        model._meta.concrete_model = target_opts.concrete_model = 'TestModel'
        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))

        field.primary_key = True
        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))

        field.primary_key = False
        field.related_model = 'AnotherModel'
        self.assertFalse(check_rel_lookup_compatibility(model, target_opts, field))

    def test_filtered_relation_eq(self):
        fr1 = FilteredRelation('relation_name', condition=Q(name='test'))
        fr2 = FilteredRelation('relation_name', condition=Q(name='test'))
        fr3 = FilteredRelation('relation_name', condition=Q(name='different'))
        self.assertEqual(fr1, fr2)
        self.assertNotEqual(fr1, fr3)

    def test_filtered_relation_clone(self):
        fr = FilteredRelation('relation_name', condition=Q(name='test'))
        clone = fr.clone()
        self.assertEqual(fr, clone)
        self.assertIsNot(fr, clone)
        self.assertEqual(fr.condition, clone.condition)

    def test_filtered_relation_repr(self):
        fr = FilteredRelation('relation_name', condition=Q(name='test'))
        self.assertIn('FilteredRelation', repr(fr))
        self.assertIn('relation_name', repr(fr))
        self.assertIn('Q(name=\'test\')', repr(fr))

    def test_q_combination_with_empty(self):
        q1 = Q(name='test')
        combined = q1 & Q()
        self.assertEqual(combined, q1)
        combined = q1 | Q()
        self.assertEqual(combined, q1)

    def test_q_negation_with_empty(self):
        negated = ~Q()
        self.assertTrue(negated.negated)
        self.assertEqual(negated.children, [])

    def test_filtered_relation_condition_empty(self):
        fr = FilteredRelation('relation_name', condition=Q())
        self.assertEqual(fr.condition, Q())

    def test_check_rel_lookup_compatibility_with_none(self):
        model = unittest.mock.Mock()
        target_opts = unittest.mock.Mock()
        field = unittest.mock.Mock()
        field.primary_key = False
        field.related_model = None

        model._meta.concrete_model = target_opts.concrete_model = 'TestModel'
        self.assertFalse(check_rel_lookup_compatibility(model, target_opts, field))

        field.primary_key = True
        self.assertTrue(check_rel_lookup_compatibility(model, target_opts, field))