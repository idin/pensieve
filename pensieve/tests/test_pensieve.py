from unittest import TestCase
from .. import Pensieve


class PensieveTestCase(TestCase):
    def setUp(self):
        self.pensieve = Pensieve()


class SetNodeTestCase(PensieveTestCase):
    def test_raises_if_name_is_none(self):
        with self.assertRaises(ValueError):
            self.pensieve.store(key=None, precursors=[], function=lambda: 'hello world')

    def test_raises_if_any_parent_is_unknown(self):
        self.pensieve.store(key='root', precursors=[], function=lambda: 'hello world')
        with self.assertRaises(KeyError):
            self.pensieve.store(
                key='child', precursors=['root', 'other'], function=lambda args: args['root'] + args['other']
            )

    def test_parents_can_be_empty_arr(self):
        self.pensieve.store(key='root', precursors=[], function=lambda: 'hello world')

    def test_parents_can_be_none(self):
        self.pensieve.store(key='root', precursors=None, function=lambda: 'hello world')


class GetValueTestCase(PensieveTestCase):

    def test_can_get_value_of_node_with_one_parent(self):
        self.pensieve.store(key='root', precursors=[], function=lambda: 5)
        self.pensieve.store(key='child', precursors=['root'], function=lambda val: val * 2)
        value = self.pensieve['child']
        self.assertEqual(value, 10)

    def test_can_get_value_of_node_with_two_parents(self):
        self.pensieve.store(key='root1', precursors=[], function=lambda: 5)
        self.pensieve.store(key='root2', precursors=[], function=lambda: 8)
        self.pensieve.store(key='child', precursors=['root1', 'root2'], function=lambda args: args.root1 + args.root2)
        value = self.pensieve['child']
        self.assertEqual(value, 13)

    def test_can_get_value_of_node_with_multiple_ancestors(self):
        self.pensieve.store(key='a', precursors=[], function=lambda: 1)
        self.pensieve.store(key='b', precursors=['a'], function=lambda val: val + 2)
        self.pensieve.store(key='c', precursors=['b'], function=lambda val: val + 4)
        self.pensieve.store(key='d', precursors=['c'], function=lambda val: val + 8)
        value = self.pensieve.d
        self.assertEqual(value, 15)

    def test_function_is_evaluated_eagerly_by_default(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number)
        number = 6
        value = self.pensieve['root']
        self.assertEqual(value, 4)

    def test_function_can_be_evaluated_lazily(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number, evaluate=False)
        number = 6
        value = self.pensieve.root
        self.assertEqual(value, 6)

    def test_parents_are_evaluated_lazily(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number, evaluate=False)
        self.pensieve.store(key='child', precursors=['root'], function=lambda val: val + 1, evaluate=False)
        number = 6
        value = self.pensieve['child']
        self.assertEqual(value, 7)

    def test_functions_are_only_evaluated_once(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number)
        self.pensieve.store(key='child', precursors=['root'], function=lambda val: val + 1, evaluate=False)
        number = 6
        value = self.pensieve['child']
        self.assertEqual(value, 5)


class GetValueAfterUpdatingNodeTestCase(PensieveTestCase):
    def test_can_update_function(self):
        self.pensieve.store(key='root', precursors=[], function=lambda: 5)
        self.pensieve.store(key='root', precursors=[], function=lambda: 9)
        value = self.pensieve['root']
        self.assertEqual(value, 9)

    def test_can_update_parents(self):
        self.pensieve.store(key='root1', precursors=[], function=lambda: 1)
        self.pensieve.store(key='root2', precursors=[], function=lambda: 3)
        self.pensieve.store(key='child', precursors=['root1'], function=lambda val: val + 5)
        value_one = self.pensieve['child']
        self.pensieve.store(key='child', precursors=['root2'], function=lambda val: val + 5)
        value_two = self.pensieve['child']
        self.assertEqual(value_one, 6)
        self.assertEqual(value_two, 8)

    def test_updating_a_node_will_cause_reevaluation_on_next_fetch(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number, evaluate=False)
        first_val = self.pensieve['root']
        number = 5
        second_val = self.pensieve['root']
        self.pensieve.store(key='root', precursors=[], function=lambda: number + 10, evaluate=False)
        third_val = self.pensieve['root']
        self.assertEqual(first_val, 4)
        self.assertEqual(second_val, 4)
        self.assertEqual(third_val, 15)

    def test_updating_a_node_will_cause_reevaluation_of_descendants_on_next_fetch(self):
        number = 4
        self.pensieve.store(key='root', precursors=[], function=lambda: number, evaluate=False)
        self.pensieve.store(key='child', precursors=['root'], function=lambda val: val + 10, evaluate=False)
        self.pensieve.store(key='grandchild', precursors=['child'], function=lambda val: val + 7, evaluate=False)
        first_val = self.pensieve['grandchild']
        number = 7
        second_val = self.pensieve['grandchild']
        self.pensieve.store(key='root', precursors=[], function=lambda: number + 100)
        third_val = self.pensieve['grandchild']
        self.assertEqual(first_val, 21)
        self.assertEqual(second_val, 21)
        self.assertEqual(third_val, 124)

    def test_function_is_only_evaluated_if_necessary(self):
        number = 2
        self.pensieve.store(key='root', precursors=[], function=lambda: 1, evaluate=False)
        self.pensieve.store(key='c1', precursors=['root'], function=lambda val: val + number + 4, evaluate=False)
        self.pensieve.store(key='c2', precursors=['root'], function=lambda val: val + number + 8, evaluate=False)
        c1_val_1 = self.pensieve['c1']
        number = 16
        c1_val_2 = self.pensieve['c1']
        c2_val = self.pensieve['c2']
        self.assertEqual(c1_val_1, 7)
        self.assertEqual(c1_val_2, 7)
        self.assertEqual(c2_val, 25)


class StrTestCase(PensieveTestCase):
    def test_can_get_str_rep_of_empty_graph(self):
        str_rep = str(self.pensieve)
        self.assertIsNotNone(str_rep)

    def test_can_get_str_rep(self):
        self.pensieve.store(key='a', precursors=[], function=lambda: 1)
        self.pensieve.store(key='b', precursors=['a'], function=lambda val: val + 2)
        self.pensieve.store(key='c', precursors=['b'], function=lambda val: val + 4)
        self.pensieve.store(key='d', precursors=['c'], function=lambda val: val + 8)
        str_rep = str(self.pensieve)
        self.assertIsNotNone(str_rep)
