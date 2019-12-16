def create_pensieve_function(function, arguments=None):
	"""
	this higher order function, takes a function f(arg1, arg2, ...)
	and produces a single argument function g(x) and returns f(arg1=x['arg1'], arg2=x['arg2'], ...)
	:param callable function: a function with a few arguments
	:param list[str] or NoneType arguments: arguments of f which would be used as keys of the dictionary argument of g
	:rtype: callable
	"""
	arguments = arguments or list(function.__code__.co_varnames)[:function.__code__.co_argcount]
	if len(arguments) == 0:
		def g():
			return function()
	elif len(arguments) == 1:
		def g(*args):
			if len(args) != 1:
				raise TypeError(f'{g.__code__.co_name}() takes one argument!')
			return function(args[0])
	else:
		def g(x):
			"""
			:type x: dict
			"""
			return function(**{var: x[var] for var in arguments})

	return g
