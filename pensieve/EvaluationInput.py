from slytherin.immutability import Immutable


class UnprotectedEvaluationInput:
	def __init__(self, inputs):
		"""
		:type inputs: dict
		"""
		self._dictionary = inputs
		not_allowed = [key for key in inputs.keys() if not self.key_allowed(key=key)]
		if len(not_allowed) > 0:
			raise KeyError(f'{not_allowed} are not allowed as input!')

	def key_allowed(self, key):
		return key not in dir(self)

	def __hashkey__(self):
		return self.__class__.__name__, self._dictionary

	def __getitem__(self, name):
		return self._dictionary[name]

	def values(self):
		return self._dictionary.values()

	def __repr__(self):
		return str(self._dictionary)

	def __str__(self):
		return self.__repr__()

	@property
	def originals(self):
		return self.__class__(
			inputs={
				key: value.original_object if isinstance(value, Immutable) else value
				for key, value in self._dictionary.items()
			}
		)


__DIRECTORY__ = dir(UnprotectedEvaluationInput({}))


class EvaluationInput(UnprotectedEvaluationInput):
	def key_allowed(self, key):
		return key not in __DIRECTORY__

	def __getattr__(self, item):
		if item in __DIRECTORY__:
			return super().__getattr__(item)
		else:
			return self[item]
