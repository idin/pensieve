from toposort import toposort
from .Memory import Memory
from slytherin.collections import remove_list_duplicates

class Pensieve:
	def __init__(self, safe=True):
		"""
		:type safe: bool
		:param safe: when True the memories are created as safe memories
		"""
		self._memories = {}
		self._precursor_keys = {}
		self._successor_keys = {}
		self._safe = safe

	def __getstate__(self):
		"""
		:rtype: dict
		"""
		state = {
			'memories': {memory_key: memory.__getstate__() for memory_key, memory in self.memories.items()},
			'precursor_keys': self._precursor_keys,
			'successor_keys': self._successor_keys,
			'safe': self._safe
		}
		return state

	def __setstate__(self, state):
		"""
		:type state: dict
		"""
		self._safe = state['safe']
		self._precursor_keys = state['precursor_keys']
		self._successor_keys = state['successor_keys']
		self._memories = {
			memory_key: Memory.from_state(state=memory_state, pensieve=self)
			for memory_key, memory_state in state['memories'].items()
		}


	@property
	def memories(self):
		"""
		:rtype: dict[str,Memory]
		"""
		return self._memories

	def freeze(self, memory):
		"""
		:type memory: Memory or str
		"""
		memory_key, memory = self._get_key_and_memory(x=memory)
		self.memories[memory_key].freeze()

	def unfreeze(self, memory):
		"""
		:type memory: Memory or str
		"""
		memory_key, memory = self._get_key_and_memory(x=memory)
		self.memories[memory_key].unfreeze()

	def _get_key_and_memory(self, x):
		"""
		:param str or Memory memory: key to memory or the memory itself
		:rtype tuple(str, Memory)
		"""
		if isinstance(x, str):
			memory_key = x
			memory = self.memories[x]
		else:
			memory = x
			memory_key = x.key
		return memory_key, memory

	def get_successors(self, memory):
		"""
		:param str or Memory memory: key to the memory you want the successor memories of
		:rtype: list[Memory]
		"""
		memory_key, _=self._get_key_and_memory(memory)
		return [self._memories[successor_key] for successor_key in self._successor_keys[memory_key]]

	def get_precursors(self, memory):
		"""
		:param str or Memory memory: key to the memory you want the precursor memories of
		:rtype: list[Memory]
		"""
		memory_key, _ = self._get_key_and_memory(memory)
		return [self._memories[precursor_key] for precursor_key in self._precursor_keys[memory_key]]

	def get_successor_keys(self, memory):
		"""
		:param str or Memory memory: key to the memory which you want the keys to its successors
		:rtype: list[str]
		"""
		memory_key, _ = self._get_key_and_memory(memory)
		return self._successor_keys[memory_key]

	def get_precursor_keys(self, memory):
		"""
		:param str or Memory memory: key to the memory which you want the keys to its precursors
		:rtype: list[str]
		"""
		memory_key, _ = self._get_key_and_memory(memory)
		return self._precursor_keys[memory_key]

	def __getitem__(self, item):
		if item in self._memories:
			memory = self._memories[item]
			result = memory.evaluate()
			return result
		else:
			raise KeyError(f'Pensieve: the "{item}" memory does not exist!')

	def store(self, key, function=None, content=None, precursors=None, evaluate=True, meta_data=None):
		"""
		:param str key: key to the new memory
		:param list[str] or NoneType precursors: key to precursor memories
		:param callable function: a function that runs on precursors and produces a new memory
		:param content: any object
		:param bool evaluate: if False the memory will not be evaluated
		"""


		if function is not None and content is not None:
			raise ValueError('Pensieve: at least one of function and content should be None!')
		elif function is None:
			function = lambda: content

		# Check inputs
		if not key:
			raise ValueError(f"Pensieve: no key provided for memory!")

		precursors = precursors or []
		precursors = remove_list_duplicates(precursors)

		# Check precursor states are known, i.e., precursor memories exist
		unknown_precursors = set(precursors).difference(set(self._memories.keys()))
		if unknown_precursors:
			precursor_str = ', '.join([f"'{s}'" for s in unknown_precursors])
			raise KeyError(f"Pensieve: error adding '{key}': Unknown precursor memories: {precursor_str}")

		# Create or update memory
		precursor_memories = remove_list_duplicates([self._memories[p] for p in precursors])

		if key in self._memories:
			memory = self._memories[key]
			memory.update(precursors=precursor_memories, function=function, meta_data=meta_data)

		else:
			memory = Memory(
				key=key, precursors=precursor_memories, function=function, pensieve=self, safe=self._safe,
				meta_data=meta_data
			)
			self._memories[key] = memory

		if evaluate:
			memory = self._memories[key]
			memory.evaluate()

	def erase(self, memory):
		"""
		:param str or Memory memory: memory to be forgotten
		:return:
		"""
		memory_key, memory = self._get_key_and_memory(x=memory)
		del self._memories[memory_key]

	def graphviz_str(self):
		dot_str = "strict digraph G { \n\t{\n "

		for memory in self._memories.values():
			node_str = f'{memory.label}'
			dot_str += f'\t\t{node_str}\n'
		dot_str += '\t}\n'
		for memory in self._memories.values():
			node_str = memory.graphviz_edges_str
			if node_str:
				dot_str += f"\t{node_str}\n"
		dot_str += "}"

		return dot_str

	def __str__(self):
		if not len(self._memories):
			return "<empty graph>"

		# Sort memories topologically
		get_dependencies = lambda n: set(n.precursor_keys)
		toposort_in = {memory.key: get_dependencies(memory) for memory in self._memories.values()}
		toposorted = [l for g in toposort(toposort_in) for l in g]

		# Find longest strings so we can pad our strings to equal length later
		get_precursors_str = lambda n: ', '.join(self._memories[n].precursor_keys)
		data_to_print = [(get_precursors_str(n), n, self._memories[n].is_stale) for n in toposorted]
		longest_precursors_str = max([len(d[0]) for d in data_to_print])
		longest_memory_key = max([len(d[1]) for d in data_to_print])

		# Build output str in format: "[precursors] --> memory" along with an indicate of stale-ness
		result_str = ""
		for data in data_to_print:
			left_side = data[0].rjust(longest_precursors_str)
			right_side = data[1].ljust(longest_memory_key)
			stale_indicator = " (stale)" if data[2] else ""
			result_str += f"{left_side} --> {right_side}{stale_indicator}\n"
		result_str = result_str.rstrip('\n')
		return result_str

	def __graph__(self):
		"""
		:rtype: dict
		"""
		return {
			'nodes': {key: memory.__graph_node__() for key, memory in self.memories.items()},
			'edges': [(parent, child) for parent, children in self._successor_keys.items() for child in children],
			'strict': True
		}



# end of file