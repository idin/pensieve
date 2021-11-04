def wrap_object(obj, name):
	class Wrap(obj.__class__):
		def __init__(self, obj=None, name=None):
			self._pensieve_obj = obj
			self._pensieve_name = name

		def __getattr__(self, item):
			if item == '_ipython_canary_method_should_not_exist_':
				raise AttributeError(item)
			if item.startswith('_pensieve'):
				return super().__getattr__(item)
			else:
				return getattr(self._pensieve_obj, item)

		def __setattr__(self, name, value):
			if name.startswith('_pensieve'):
				return super().__setattr__(name, value)
			else:
				setattr(self._pensieve_obj, name, value)

		def __delattr__(self, *args, **kwargs):
			return self._pensieve_obj.__delattr__(*args, **kwargs)

		def __dict__(self, *args, **kwargs):
			return self._pensieve_obj.__dict__(*args, **kwargs)

		def __dir__(self, *args, **kwargs):
			return self._pensieve_obj.__dir__(*args, **kwargs)

		def __doc__(self, *args, **kwargs):
			return self._pensieve_obj.__doc__(*args, **kwargs)

		def __eq__(self, *args, **kwargs):
			return self._pensieve_obj.__eq__(*args, **kwargs)

		def __format__(self, *args, **kwargs):
			return self._pensieve_obj.__format__(*args, **kwargs)

		def __ge__(self, *args, **kwargs):
			return self._pensieve_obj.__ge__(*args, **kwargs)

		def __gt__(self, *args, **kwargs):
			return self._pensieve_obj.__gt__(*args, **kwargs)

		def __hash__(self, *args, **kwargs):
			return hash(self._pensieve_obj)

		def __init_subclass__(self, *args, **kwargs):
			return self._pensieve_obj.__init_subclass__(*args, **kwargs)

		def __le__(self, *args, **kwargs):
			return self._pensieve_obj.__le__(*args, **kwargs)

		def __lt__(self, *args, **kwargs):
			return self._pensieve_obj.__lt__(*args, **kwargs)

		def __module__(self, *args, **kwargs):
			return self._pensieve_obj.__module__(*args, **kwargs)

		def __ne__(self, *args, **kwargs):
			return self._pensieve_obj.__ne__(*args, **kwargs)

		def __reduce__(self, *args, **kwargs):
			return self._pensieve_obj.__reduce__(*args, **kwargs)

		def __reduce_ex__(self, *args, **kwargs):
			return self._pensieve_obj.__reduce_ex__(*args, **kwargs)

		def __repr__(self, *args, **kwargs):
			return self._pensieve_obj.__repr__(*args, **kwargs)

		def __sizeof__(self, *args, **kwargs):
			return self._pensieve_obj.__sizeof__(*args, **kwargs)

		def __str__(self, *args, **kwargs):
			return self._pensieve_obj.__str__(*args, **kwargs)

		def __subclasshook__(self, *args, **kwargs):
			return self._pensieve_obj.__subclasshook__(*args, **kwargs)

		def __weakref__(self, *args, **kwargs):
			return self._pensieve_obj.__weakref__(*args, **kwargs)

	y = Wrap(obj=obj, name=name)

	return y
