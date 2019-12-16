from .Pensieve import Pensieve as OriginalPensieve
__DIRECTORY__ = dir(OriginalPensieve())
__DIRECTORY__.append('__deepcopy__')
__DIRECTORY__.append('global')


class Pensieve(OriginalPensieve):
	def key_allowed(self, key):
		return key not in __DIRECTORY__

	def __getattr__(self, item):
		if item in __DIRECTORY__:
			return super().__getattr__(item)
		else:
			return self[item]

	def __setattr__(self, key, value):
		if key in __DIRECTORY__:
			super().__setattr__(key, value)
		else:
			self[key] = value

	def __dir__(self):
		return list(self.memories_dictionary.keys()) + super().__dir__()
