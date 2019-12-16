class PensieveError(Exception):
	pass

class MissingMemoryError(PensieveError):
	pass

class StoringError(PensieveError):
	pass

class UnknownPrecursorError(StoringError):
	pass

class MemoryRecursionError(StoringError):
	pass

class IllegalKeyError(StoringError):
	pass