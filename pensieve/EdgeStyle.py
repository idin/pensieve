from copy import deepcopy


class EdgeStyle:
	def __init__(self, colour=None, arrow_size=None, **kwargs):
		dictionary = {
			'color': colour,
			'arrowsize': arrow_size
		}
		self._dictionary = {}
		for key, value in dictionary.items():
			if value is not None:
				self._dictionary[key] = value
		for key, value in kwargs.items():
			if value is not None:
				self._dictionary[key] = value

	def complement(self, original_style):
		"""
		:type original_style: EdgeStyle
		"""
		if original_style is None:
			return deepcopy(self)
		elif type(original_style) is not EdgeStyle:
			raise TypeError(f'original_style:{original_style} is of type: {type(original_style)}')
		dictionary = self._dictionary.copy()
		if original_style is not None:
			for key, value in original_style._dictionary.items():
				if key not in dictionary:
					dictionary[key] = value
		return self.__class__(**dictionary)

	def __str__(self):
		return '[' + ' '.join([f'{key}={value}' for key, value in self._dictionary.items()]) + ']'

	def __repr__(self):
		return str(self._dictionary)
