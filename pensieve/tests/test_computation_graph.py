from unittest import TestCase
from .. import ComputationGraph


class ComputationGraphTestCase(TestCase):
    def setUp(self):
        self.graph = ComputationGraph()


class SetNodeTestCase(ComputationGraphTestCase):
    def test_raises_if_name_is_none(self):
        with self.assertRaises(ValueError):
            self.graph.add(name=None, parents=[], function=lambda: 'hello world')

    def test_raises_if_any_parent_is_unknown(self):
        self.graph.add(name='root', parents=[], function=lambda: 'hello world')
        with self.assertRaises(KeyError):
            self.graph.add(name='child', parents=['root', 'other'], function=lambda args: args['root'] + args['other'])

    def test_parents_can_be_empty_arr(self):
        self.graph.add(name='root', parents=[], function=lambda: 'hello world')

    def test_parents_can_be_none(self):
        self.graph.add(name='root', parents=None, function=lambda: 'hello world')


class GetValueTestCase(ComputationGraphTestCase):
    def test_can_get_root_value(self):
        self.graph.add(name='root', parents=[], function=lambda: 'hello world')
        value = self.graph.root
        self.assertEqual(value, 'hello world')

    def test_can_get_value_of_node_with_one_parent(self):
        self.graph.add(name='root', parents=[], function=lambda: 5)
        self.graph.add(name='child', parents=['root'], function=lambda val: val * 2)
        value = self.graph.child
        self.assertEqual(value, 10)

    def test_can_get_value_of_node_with_two_parents(self):
        self.graph.add(name='root1', parents=[], function=lambda: 5)
        self.graph.add(name='root2', parents=[], function=lambda: 8)
        self.graph.add(name='child', parents=['root1', 'root2'], function=lambda args: args.root1 + args.root2)
        value = self.graph.child
        self.assertEqual(value, 13)

    def test_can_get_value_of_node_with_multiple_ancestors(self):
        self.graph.add(name='a', parents=[], function=lambda: 1)
        self.graph.add(name='b', parents=['a'], function=lambda val: val + 2)
        self.graph.add(name='c', parents=['b'], function=lambda val: val + 4)
        self.graph.add(name='d', parents=['c'], function=lambda val: val + 8)
        value = self.graph.d
        self.assertEqual(value, 15)

    def test_function_is_evaluated_eagerly_by_default(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number)
        number = 6
        value = self.graph.root
        self.assertEqual(value, 4)

    def test_function_can_be_evaluated_lazily(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number, evaluate=False)
        number = 6
        value = self.graph.root
        self.assertEqual(value, 6)

    def test_parents_are_evaluated_lazily(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number, evaluate=False)
        self.graph.add(name='child', parents=['root'], function=lambda val: val + 1, evaluate=False)
        number = 6
        value = self.graph.child
        self.assertEqual(value, 7)

    def test_functions_are_only_evaluated_once(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number)
        self.graph.add(name='child', parents=['root'], function=lambda val: val + 1, evaluate=False)
        number = 6
        value = self.graph.child
        self.assertEqual(value, 5)


class GetValueAfterUpdatingNodeTestCase(ComputationGraphTestCase):
    def test_can_update_function(self):
        self.graph.add(name='root', parents=[], function=lambda: 5)
        self.graph.add(name='root', parents=[], function=lambda: 9)
        value = self.graph.root
        self.assertEqual(value, 9)

    def test_can_update_parents(self):
        self.graph.add(name='root1', parents=[], function=lambda: 1)
        self.graph.add(name='root2', parents=[], function=lambda: 3)
        self.graph.add(name='child', parents=['root1'], function=lambda val: val + 5)
        value_one = self.graph.child
        self.graph.add(name='child', parents=['root2'], function=lambda val: val + 5)
        value_two = self.graph.child
        self.assertEqual(value_one, 6)
        self.assertEqual(value_two, 8)

    def test_updating_a_node_will_cause_reevaluation_on_next_fetch(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number, evaluate=False)
        first_val = self.graph.root
        number = 5
        second_val = self.graph.root
        self.graph.add(name='root', parents=[], function=lambda: number + 10, evaluate=False)
        third_val = self.graph.root
        self.assertEqual(first_val, 4)
        self.assertEqual(second_val, 4)
        self.assertEqual(third_val, 15)

    def test_updating_a_node_will_cause_reevaluation_of_descendants_on_next_fetch(self):
        number = 4
        self.graph.add(name='root', parents=[], function=lambda: number, evaluate=False)
        self.graph.add(name='child', parents=['root'], function=lambda val: val + 10, evaluate=False)
        self.graph.add(name='grandchild', parents=['child'], function=lambda val: val + 7, evaluate=False)
        first_val = self.graph.grandchild
        number = 7
        second_val = self.graph.grandchild
        self.graph.add(name='root', parents=[], function=lambda: number + 100)
        third_val = self.graph.grandchild
        self.assertEqual(first_val, 21)
        self.assertEqual(second_val, 21)
        self.assertEqual(third_val, 124)

    def test_function_is_only_evaluated_if_necessary(self):
        number = 2
        self.graph.add(name='root', parents=[], function=lambda: 1, evaluate=False)
        self.graph.add(name='c1', parents=['root'], function=lambda val: val + number + 4, evaluate=False)
        self.graph.add(name='c2', parents=['root'], function=lambda val: val + number + 8, evaluate=False)
        c1_val_1 = self.graph.c1
        number = 16
        c1_val_2 = self.graph.c1
        c2_val = self.graph.c2
        self.assertEqual(c1_val_1, 7)
        self.assertEqual(c1_val_2, 7)
        self.assertEqual(c2_val, 25)


class StrTestCase(ComputationGraphTestCase):
    def test_can_get_str_rep_of_empty_graph(self):
        str_rep = str(self.graph)
        self.assertIsNotNone(str_rep)

    def test_can_get_str_rep(self):
        self.graph.add(name='a', parents=[], function=lambda: 1)
        self.graph.add(name='b', parents=['a'], function=lambda val: val + 2)
        self.graph.add(name='c', parents=['b'], function=lambda val: val + 4)
        self.graph.add(name='d', parents=['c'], function=lambda val: val + 8)
        str_rep = str(self.graph)
        self.assertIsNotNone(str_rep)
