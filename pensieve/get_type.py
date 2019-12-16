from slytherin.immutability import Immutable
from collections import Counter

BUILTIN_TYPES = {
	'list': 'List',
	'dict': 'Dictionary',
	'str': 'String',
	'int': 'Integer',
	'float': 'Float',
	'bool': 'Boolean',
	'tuple': 'Tuple',
	'set': 'Set',
	'object': 'Object',
	'long': 'Long',
	'function': 'Function'
}


def _get_type(x):
	if isinstance(x, Immutable):
		x = x._original_object
	name = type(x).__name__
	return BUILTIN_TYPES.get(name, name)


def _verbalize(type_name, type_count):
	if type_count == 1:
		return f'1 {type_name}'
	else:
		type_plural = f'{type_name[:-1]}ies' if type_name.endswith('y') else f'{type_name}s'
		return f'{type_count} {type_plural}'


def get_type(x):
	parent_type = _get_type(x)
	if isinstance(x, (list, tuple, dict)):

		if isinstance(x, (list, tuple)):
			elements = x
			if isinstance(x, list):
				prefix, suffix = '[', ']'
			else:
				prefix, suffix = '(', ')'
		else:
			prefix, suffix = '{', '}'
			elements = list(x.values())

		if len(elements) == 0:
			text = f'{parent_type}: empty'
		else:
			types = dict(Counter(_get_type(element) for element in elements))
			texts = [
				_verbalize(type_name=type_name, type_count=type_count) for type_name, type_count in types.items()
			]

			text = ', '.join(texts)
		return f'{prefix} {text} {suffix}'

	else:
		try:
			shape = x.shape
			if isinstance(shape, (tuple, list)):
				shape = ': ' + '×'.join([str(x) for x in shape])
			else:
				shape = ''
		except AttributeError:
			shape = ''

		return f'< {parent_type}{shape} >'
