from slytherin.collections import remove_list_duplicates
from slytherin import get_size
from slytherin.hash import hash_object
import dill
from datetime import datetime
from .EvaluationInput import EvaluationInput


def get_elapsed_seconds(start, end=None):
	end = end or datetime.now()
	delta = end - start
	return delta.seconds + delta.microseconds / 1E6


class Memory:
	def __init__(
			self, key, pensieve, function, precursors=None, safe=True, metadata=False, materialize=True,
			_update=True, _stale=True
	):
		"""
		:param str key: unique name/identifier of the memory
		:param Pensieve pensieve: the pensieve this memory belongs to
		:param callable function: a function to be called on precursor memories
		:param list[Memory] or NoneType precursors: precursor memories to this memory
		:param bool safe: when True only a copy of the content is returned to avoid mutating it from outside
		:param dict metadata: an optional dictionary that carries meta data about this memory
		:param bool materialize: when False, this memory runs the function everyone it needs the content, rather than keeping it
		:param bool _update: if True the precursors will be updated
		:param bool _stale:
		"""
		# make precursors unique
		precursors = precursors or []
		self._key = key
		self._pensieve = pensieve
		self._content = None
		self._materialize = materialize
		self._safe = safe
		if self.key not in self.pensieve._successor_keys:
			self.pensieve._successor_keys[self.key] = []
		if self.key not in self.pensieve._precursor_keys:
			self.pensieve._precursor_keys[self.key] = []
		self._frozen = False
		self._stale = _stale
		self._function = None
		self._metadata = metadata or {}
		self._last_evaluated = None
		self._evaluation_time = None
		self._total_time = None
		self._size = None
		self._content_hash = None

		if _update:
			self.update(precursors, function)

	def get_summary(self, time_unit='ms'):
		time_coefficients = {
			'ms': 1e3,
			'millisecond': 1e3,
			'us': 1e6,
			'microsecond': 1e6
		}
		time_coefficient = time_coefficients[time_unit] if time_unit in time_coefficients else 1

		result = {
			'key': self.key,
			'content_type': type(self.content).__name__,
			'materialized': self._materialize,
			'frozen': self._frozen,
			'last_evaluated': self._last_evaluated,
			'evaluation_time': self.evaluation_time * time_coefficient,
			'total_time': self.total_time * time_coefficient,
			'size': self.size,
			'content_hash': self._content_hash,
			'precursors': self.precursor_keys
		}
		for key, value in self._metadata:
			new_key = f'metadata_{key}' if key in result else key
			result[new_key] = value
		return result

	@property
	def size(self):
		if self._size is None:
			result = 0
			result += get_size(self._key, exclude_objects=[self._pensieve])
			result += get_size(self._content, exclude_objects=[self._pensieve])
			result += get_size(self._content_hash, exclude_objects=[self._pensieve])
			result += get_size(self._safe, exclude_objects=[self._pensieve])
			result += get_size(self._frozen, exclude_objects=[self._pensieve])
			result += get_size(self._stale, exclude_objects=[self._pensieve])
			result += get_size(self._function, exclude_objects=[self._pensieve])
			result += get_size(self._metadata, exclude_objects=[self._pensieve])
			result += get_size(self._last_evaluated, exclude_objects=[self._pensieve])
			result += get_size(self._evaluation_time, exclude_objects=[self._pensieve])
			result += get_size(result)
			self._size = result
		return self._size

	@property
	def evaluation_time(self):
		if self._evaluation_time is None:
			self.get_content_and_hash()
		return self._evaluation_time

	@property
	def total_time(self):
		if self._total_time is None:
			if len(self.precursor_keys) == 0:
				self._total_time = self.evaluation_time
			else:
				self._total_time = self.evaluation_time + sum([precursor.total_time for precursor in self.precursors])
		return self._total_time

	@property
	def speed(self):
		if self._evaluation_time:
			return self.size/self._evaluation_time
		else:
			return None

	def __sizeof__(self):
		return self.size

	def __eq__(self, other):
		return isinstance(other, Memory) and self.key == other.key

	def __hash__(self):
		return self.key.__hash__()

	def __repr__(self):
		return f'Memory:{self.key}'

	def __getstate__(self):
		"""
		:rtype: dict
		"""
		stale = self._stale
		try:
			content = dill.dumps(obj=self._content)
		except Exception as e:
			# if we fail to serialize the content of the memory we store it as stale
			# so the next time it is remembered, i.e., loaded, it will be reconstructed
			print(f'Could not save content of memory: "{self.key}"')
			print(f'Exception thrown:', e)
			content = dill.dumps(obj=None)
			stale = True

		state = {
			'key': self._key,
			'content': content,
			'previous_input_hash': self._content_hash,
			'safe': self._safe,
			'frozen': self._frozen,
			'stale': stale,
			'metadata': self._metadata,
			'function': dill.dumps(obj=self._function),
			'last_evaluated': self._last_evaluated,
			'elapsed_seconds': self._evaluation_time
		}
		return state

	def __setstate__(self, state):
		"""
		:type state: dict
		"""
		self._key = state['key']
		self._content = dill.loads(str=state['content'])
		self._content_hash = state['previous_input_hash']
		self._safe = state['safe']
		self._frozen = state['frozen']
		self._stale = state['stale']
		self._metadata = state['metadata']
		self._function = dill.loads(str=state['function'])
		self._pensieve = None
		self._last_evaluated = state['last_evaluated']
		self._evaluation_time = state['elapsed_seconds']

	@classmethod
	def from_state(cls, state, pensieve):
		memory = Memory(
			key=state['key'],
			function=dill.loads(str=state['function']),
			pensieve=pensieve,
			precursors=None,
			safe=state['safe'],
			metadata=state['metadata'],
			_update=False, _stale=state['stale']
		)
		try:
			memory._content = dill.loads(str=state['content'])
		except Exception as e:
			print(f'Could not load content for memory: "{memory.key}"')
			print(f'Exception thrown:', e)
			memory._content = None

		memory._frozen = state['frozen']
		memory._stale = state['stale']
		memory._last_evaluated = state['last_evaluated']
		memory._evaluation_time = state['elapsed_seconds']
		return memory

	@property
	def is_frozen(self):
		return self._frozen

	@property
	def is_stale(self):
		return self._stale

	def freeze(self):
		self._frozen = True

	def unfreeze(self):
		self._frozen = False
		if self._stale:
			self.mark_stale()

	@property
	def pensieve(self):
		"""
		:rtype: .Pensieve.Pensieve
		"""
		return self._pensieve

	@property
	def key(self):
		return self._key

	@property
	def label(self):
		key = self.key.replace('__', '\n').replace('_', ' ')
		if self.is_stale and self.is_frozen:
			return f'{key}\n(stale & frozen)'
		elif self.is_stale and not self.is_frozen:
			return f'{key}\n(stale)'
		elif not self.is_stale and self.is_frozen:
			return f'{key}\n(frozen)'
		else:
			return f'{key}'

	@property
	def precursor_keys(self):
		"""
		:type: list[str]
		"""
		return list(self.pensieve.get_precursor_keys(memory=self))

	@property
	def successors(self):
		return self.pensieve.get_successors(memory=self)

	@property
	def has_precursors(self):
		return len(self.precursor_keys) > 0

	@property
	def successor_keys(self):
		"""
		:type: list[str]
		"""
		return list(self.pensieve.get_successor_keys(memory=self))

	@property
	def precursors(self):
		return self.pensieve.get_precursors(memory=self)

	@property
	def has_successors(self):
		return len(self.successor_keys) > 0

	def erase_successor(self, successor):
		"""
		:param Memory or str successor: the successor memory or its key that should be removed
		"""
		if isinstance(successor, str):
			self.pensieve._successor_keys[self.key].remove(successor)
		else:
			self.pensieve._successor_keys[self.key].remove(successor.key)

	# ************************* COMPUTATION **********************************

	def update(self, precursors, function, metadata=None, materialize=None):
		"""
		:type precursors: list[Memory]
		:type function: callable
		:type metadata: NoneType or dict
		"""
		# make precursors unique:
		precursors = precursors or []
		precursors = remove_list_duplicates(precursors)

		precursor_keys = [p.key for p in precursors]

		removed_precursor_keys = [key for key in self.precursor_keys if key not in precursor_keys]
		new_precursor_keys = [key for key in precursor_keys if key not in self.precursor_keys]

		self.pensieve._precursor_keys[self.key] = precursor_keys
		for precursor_key in removed_precursor_keys:
			self.pensieve._successor_keys[precursor_key].remove(self.key)
		for precursor_key in new_precursor_keys:
			self.pensieve._successor_keys[precursor_key].append(self.key)

		self._function = function
		self.mark_stale()

		if metadata is not None:
			self._metadata = metadata
		if materialize is not None:
			self._materialize = materialize

	def evaluate(self):
		content = self.content

	@property
	def content(self):
		if not self._materialize:
			self.set_content(content=None, content_hash=None)
			content, content_hash = self.get_content_and_hash()
			return content
		elif self.is_frozen or not self.is_stale:
			return self._content
		else:
			content, content_hash = self.get_content_and_hash()
			self.set_content(content=content, content_hash=content_hash)
			return self._content

	def set_content(self, content, content_hash):
		if self.is_frozen:
			raise RuntimeError('Memory: You cannot change a frozen memory!')
		self._content = content
		self._stale = False
		self._content_hash = content_hash

	def mark_stale(self):
		if self._materialize:
			self._stale = True
		self._size = None
		for successor in self.successors:
			successor.mark_stale()

	def get_content_and_hash(self):
			precursor_keys_to_contents = {p.key: p.content for p in self.precursors}



			if len(self.precursor_keys) == 0:
				new_hash = hash_object(self._function)
				if new_hash == self._content_hash and self._materialize:
					new_content = self._content

				else:
					start_time = datetime.now()
					new_content = self._function()
					self._evaluation_time = get_elapsed_seconds(start=start_time)

			elif len(self.precursor_keys) == 1:
				precursor_content = list(precursor_keys_to_contents.values())[0]
				new_hash = hash_object((self._function, precursor_content))
				if new_hash == self._content_hash and self._materialize:
					new_content = self._content

				else:
					start_time = datetime.now()
					new_content = self._function(precursor_content)
					self._evaluation_time = get_elapsed_seconds(start=start_time)

			else:
				inputs = EvaluationInput(inputs=precursor_keys_to_contents)
				new_hash = hash_object((self._function, inputs))
				if new_hash == self._content_hash and self._materialize:
					new_content = self._content

				else:
					start_time = datetime.now()
					new_content = self._function(inputs)
					self._evaluation_time = get_elapsed_seconds(start=start_time)


			self._last_evaluated = datetime.now()
			return new_content, new_hash

	@property
	def graphviz_edges_str(self):
		if not self.has_precursors:
			return self.label if not self.has_successors else None
		else:
			edges = [
				f'{precursor.label} -> {self.label}'
				for precursor in self.precursors
			]
			return '\n'.join(edges)

	def __graph_node__(self):
		"""
		:rtype: dict
		"""
		return {
			'label': self.label,
			'value': None,
			'metadata': self._metadata
		}
