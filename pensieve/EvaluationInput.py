class EvaluationInput:
	def __init__(self, inputs):
		self._dictionary = inputs

	def __getitem__(self, name):
		return self._dictionary[name]

	def __repr__(self):
		return str(self._dictionary)

	def __str__(self):
		return self.__repr__()
