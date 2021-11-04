from .Memory import Memory
from .create_pensieve_function import create_pensieve_function
from .exceptions import *
from .get_schedule import get_schedule

from slytherin.collections import remove_list_duplicates
from slytherin import get_function_arguments
from chronometry import MeasurementSet, convert
from chronometry.progress import ProgressBar
from joblib import Parallel
from joblib import delayed

from toposort import toposort
import warnings
from copy import deepcopy
from disk import Path
from abstract import Graph


class Directory:
	def __init__(self, pensieve):
		self._pensieve = pensieve

	def __getstate__(self):
		return {}

	def __setstate__(self, state):
		pass

	def __getattr__(self, item):
		if item in self._pensieve.memories_dictionary:
			return item
		else:
			raise MissingMemoryError(f'{item} does not exist in pensieve')

	def __dir__(self):
		return list(self._pensieve.memories_dictionary.keys())


class Pensieve:
	def __init__(
			self, safe=False, name='Pensieve', function_durations=None, warn_unsafe=False, hide_ignored=False,
			graph_direction='LR', num_threads=1, evaluate=True, materialize=True, backup=False, echo=0,
			hash=True, n_jobs=1
	):
		"""
		:param bool 	safe: 				if True, pensieve memories will be safe from mutations
		:param str		name:				a name for pensieve
		:param bool 	hide_ignored: 		if True, ignored nodes will be hidden
		:param str 		graph_direction: 	'LR' for left to right, 'UD' for up-down
		:param int 		num_threads: 		number of concurrent threads to use in processing, -1 for auto
		:param bool 	evaluate: 			to evaluate each node immediately or lazily
		:param bool 	materialize: 		if False, calculated nodes will not be materialized into memory

		:param MeasurementSet 						function_durations: 	time measurements of memory functions
		:param bool or int or ProgressBar 			echo: 					int or ProgressBar or bool
		"""
		self._graph_direction = graph_direction
		self._memories_dictionary = {}
		self._precursor_keys = {}
		self._successor_keys = {}
		if not safe and warn_unsafe:
			warnings.warn('Memory contents can be mutated outside a safe pensieve!')
		self._safe = safe
		self._name = name
		self._warn_safe = warn_unsafe
		self._function_durations = function_durations or MeasurementSet()
		self._directory = Directory(pensieve=self)
		self._hide_ignored = hide_ignored
		self._num_intermediary_nodes = 0
		self._num_threads = num_threads
		self._evaluate = evaluate
		self._materialize = materialize
		self._echo = echo
		self._do_hash = hash
		self._n_jobs = n_jobs
		if backup:
			if isinstance(backup, bool):
				backup = 'pensieve'
			self._backup_directory = Path(backup)
			self._backup_directory.make_dir(ignore_if_exists=True)
			self._backup_memory_directory = self.backup_directory.make_dir(name='memories', ignore_if_exists=True)

		else:
			self._backup_directory = None
			self._backup_memory_directory = None

	_PARAMETERS_ = ['safe', 'name', 'warn_safe', 'function_durations', 'hide_ignored', 'precursor_keys', 'successor_keys']
	_STATE_ATTRIBUTES_ = [
		'_graph_direction', '_name',
		'_memories_dictionary', '_precursor_keys', '_successor_keys',
		'_safe', '_warn_safe', '_function_durations', '_directory', '_hide_ignored',
		'_num_intermediary_nodes', '_num_threads', '_evaluate', '_materialize', '_echo',
		'_backup_directory', '_backup_memory_directory'
	]

	def __getstate__(self):
		return {key: getattr(self, key) for key in self._STATE_ATTRIBUTES_}

	def _make_state_backward_compatibile(self, state):
		result = {
			'_memories_dictionary': {
				memory_key: Memory._backward_compatible_from_state(state=memory_state)
				for memory_key, memory_state in state['memories'].items()
			},
			'_graph_direction': 'LR',
			'_precursor_keys': state['precursor_keys'],
			'_successor_keys': state['successor_keys'],
			'_safe': state['safe'],
			'_warn_safe': False,
			'_function_durations': MeasurementSet(),
			'_directory': Directory(pensieve=self),
			'_hide_ignored': False,
			'_num_intermediary_nodes': 0,
			'_num_threads': 1,
			'_evaluate': True,
			'_materialize': True,
			'_echo': 0,
			'_backup_directory': None,
			'_backup_memory_directory': None
		}
		return result

	def __setstate__(self, state):
		# backward compatibility
		if all([key in state for key in ['memories', 'precursor_keys', 'successor_keys', 'safe']]):
			state = self._make_state_backward_compatibile(state=state)

		for key, value in state.items():
			setattr(self, key, value)
		for key in Pensieve._STATE_ATTRIBUTES_:
			if key not in state:
				print(f'missing attribute: {key}')
				setattr(self, key, None)
		for memory in self.memories_dictionary.values():
			memory._pensieve = self
		self._directory._pensieve = self

	@property
	def processor(self):
		"""
		:rtype: NoneType or Parallel
		"""
		return Parallel(n_jobs=self._num_threads, backend='threading', require='sharedmem')

	def get_update_schedule(self, keys):
		jobs = []
		for key in keys:
			for job in self.memories_dictionary[key].stale_dependencies:
				if job not in jobs:
					jobs.append(job)
		for key in keys:
			if self.memories_dictionary[key].is_stale:
				jobs.append(self.memories_dictionary[key])
		return get_schedule(jobs=jobs)

	def evaluate(self, keys=None, output=False):
		"""
		evaluates multiple memories, in parallel if num_threads != 1
		:type keys: list[str] or NoneType or str
		:type output: bool
		:rtype: list or NoneType
		"""
		if keys is None:
			keys = list(self.memories_dictionary.keys())
		elif isinstance(keys, str):
			keys = [keys]

		if self._num_threads == 1:
			if output:
				return [self[key] for key in keys]
			else:
				for key in keys:
					self.memories_dictionary[key].evaluate()
		else:
			def get_content(p):
				return p.content

			memories = [self.memories_dictionary[key] for key in keys]
			schedule = self.get_update_schedule(keys=keys)

			progress_bar = ProgressBar(
				total=sum([len(schedule_round) for schedule_round in schedule]),
				echo=self._echo
			)

			progress_amount = 0
			for schedule_round in schedule:
				progress_bar.show(amount=progress_amount, text=f'updating {len(schedule_round)} memories')
				self.processor(delayed(get_content)(job) for job in schedule_round)
				progress_amount += len(schedule_round)
			if progress_amount > 0:
				progress_bar.show(amount=progress_amount, text=f'{self.key} updated!')

			contents = self.processor(delayed(get_content)(p) for p in memories)
			if output:
				return list(contents)

	@property
	def backup_directory(self):
		"""
		:rtype: Path or NoneType
		"""
		return self._backup_directory

	@property
	def backup_memory_directory(self):
		"""
		:rtype: Path or NoneType
		"""
		return self._backup_memory_directory

	def __add__(self, other):
		"""
		:type other: Pensieve
		:rtype: Pensieve
		"""
		new_pensieve = self.__class__(
			safe=self._safe, function_durations=self.function_durations, warn_unsafe=self._warn_safe,
			hide_ignored=self._hide_ignored, graph_direction=self._graph_direction
		)
		memories_dictionary = {}
		precursor_keys = {}
		successor_keys = {}
		stales = []

		for key in set(self.memories_dictionary.keys()).union(set(other.memories_dictionary.keys())):

			if key in self.memories_dictionary and key not in other.memories_dictionary:
				new_memory = self.memories_dictionary[key].partial_copy(
					include_function=True, include_precursor_hash=False,
					stale=self.memories_dictionary[key].is_stale
				)
				precursor_keys[key] = self._precursor_keys[key].copy()
				successor_keys[key] = self._successor_keys[key].copy()
				if self.memories_dictionary[key].is_stale:
					stales.append(key)

			elif key in other.memories_dictionary and key not in self.memories_dictionary:
				new_memory = other.memories_dictionary[key].partial_copy(
					include_function=True, include_precursor_hash=False,
					stale=other.memories_dictionary[key].is_stale
				)
				precursor_keys[key] = other._precursor_keys[key].copy()
				successor_keys[key] = other._successor_keys[key].copy()
				if other.memories_dictionary[key].is_stale:
					stales.append(key)

			else:
				left_memory = self.memories_dictionary[key]
				right_memory = other.memories_dictionary[key]

				if not right_memory.has_precursors:
					new_memory = left_memory.partial_copy(
						include_function=True, include_precursor_hash=False, stale=True
					)
					precursor_keys[key] = self._precursor_keys[key].copy()

				elif not left_memory.has_precursors:
					new_memory = right_memory.partial_copy(
						include_function=True, include_precursor_hash=False, stale=True
					)
					precursor_keys[key] = other._precursor_keys[key].copy()

				else:
					raise PensieveError(f'memory "{key}" has precursors in both pensieves')

				stales.append(key)

				successor_keys[key] = self._successor_keys[key].copy()
				for x in other._successor_keys[key]:
					if x not in successor_keys[key]:
						successor_keys[key].append(x)

			new_memory._pensieve = new_pensieve
			memories_dictionary[key] = new_memory

		new_pensieve._precursor_keys = precursor_keys
		new_pensieve._successor_keys = successor_keys
		new_pensieve._memories_dictionary = memories_dictionary
		for stale in stales:
			new_pensieve._memories_dictionary[stale].mark_stale()

		return new_pensieve

	def __hashkey__(self):
		return self.__class__.__name__, self.parameters, self.__getstate__()

	def __getattr__(self, item):
		return self.__getattribute__(item)

	@property
	def parameters(self):
		return {param: getattr(self, f'_{param}') for param in self._PARAMETERS_}

	def save(self, path, echo=None):
		"""
		:type path: str or Path
		:type echo: bool
		"""
		if echo is None:
			echo = self._echo

		progress_bar = ProgressBar(total=len(self.memories_dictionary)+2, echo=echo)
		progress_amount = 0

		path = Path(string=path)
		path.make_dir()

		progress_bar.show(amount=progress_amount, text='saving parameters')
		(path + 'parameters.pensieve').save(obj=self.parameters)
		progress_amount += 1

		memory_keys = []

		for key, memory in self.memories_dictionary.items():
			progress_bar.show(amount=progress_amount, text=f'saving "{key}" memory')
			memory.save(path=path + key)
			progress_amount += 1
			memory_keys.append(key)

		progress_bar.show(amount=progress_amount, text=f'saving memory keys')
		(path + 'memory_keys.pensieve').save(obj=memory_keys)
		progress_amount += 1

		progress_bar.show(amount=progress_amount)

	@classmethod
	def load(cls, path, echo=True):
		path = Path(string=path)
		parameters = (path + 'parameters.pensieve').load()
		pensieve = cls(safe=parameters['safe'])
		for name, value in parameters.items():
			setattr(pensieve, f'_{name}', value)
		memory_keys = (path + 'memory_keys.pensieve').load()
		progress_bar = ProgressBar(total=len(memory_keys))
		progress_amount = 0
		pensieve._memories_dictionary = {}
		for key in memory_keys:
			if echo:
				progress_bar.show(amount=progress_amount, text=f'loading "{key}" memory')
			memory = Memory.load(path=path + key, pensieve=pensieve)
			pensieve._memories_dictionary[key] = memory
			progress_amount += 1
		if echo:
			progress_bar.show(amount=progress_amount)
		return pensieve

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False

		all_keys = set(self.memories_dictionary.keys()).union(other.memories_dictionary.keys())
		for key in all_keys:
			if key not in self.memories_dictionary or key not in other.memories_dictionary:
				return False
			if self.memories_dictionary[key] != other.memories_dictionary[key]:
				return False

		return True

	def __ge__(self, other):
		#  >= means the other pensieve is either equal to this or is a subset of
		if not isinstance(other, self.__class__):
			return False

		for key in other.memories_dictionary.keys():
			if key not in self.memories_dictionary:
				return False
			if self.memories_dictionary[key] != other.memories_dictionary[key]:
				return False
		return True

	def __gt__(self, other):
		#  > means the other pensieve is a subset of this one but not equal
		if not isinstance(other, self.__class__):
			return False

		if not self >= other:
			return False
		for key in self.memories_dictionary.keys():
			if key not in other.memories_dictionary:
				return True
		return False

	def __lt__(self, other):
		return other > self

	def __le__(self, other):
		return other >= self

	@property
	def directory(self):
		"""
		:rtype: Directory
		"""
		return self._directory

	dir = directory
	key = directory
	memory = directory
	using = directory

	def get_graph(self, direction='LR'):
		"""
		:type direction: str
		:rtype: Graph
		"""
		return Graph(obj=self, direction=direction)

	def display(self, p=None, dpi=300, hide_ignored=None, direction=None, pad=None, path=None, height=None, width=None):
		if hide_ignored is None:
			hide_ignored = self._hide_ignored
		original_hide_ignored = self._hide_ignored
		self._hide_ignored = hide_ignored
		graph = self.get_graph(direction=self._graph_direction)
		self._hide_ignored = original_hide_ignored

		if graph is None:
			print(str(self))
		else:
			graph.display(
				p=p, dpi=dpi, direction=direction or self._graph_direction, path=path, height=height, width=width,
				pad=pad
			)

		if graph is None:
			return None
		else:
			return graph.get_html(direction=direction, pad=pad)

	def _repr_html_(self):
		return self.get_svg()

	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text('Pensieve')
		else:
			self.display(p=p)

	def get_svg(self, direction=None, pad=None, **kwargs):
		"""
		:type direction: NoneType or str
		:type pad: NoneType or int or float
		:rtype: str
		"""
		return self.get_graph(direction=self._graph_direction).get_svg(direction=direction, pad=pad, **kwargs)

	def get_html(self, direction=None, pad=None, **kwargs):
		return self.get_graph(direction=self._graph_direction).get_html(direction=direction, pad=pad, **kwargs)

	def display_html(self, direction=None, pad=None, **kwargs):
		graph = self.get_graph(direction=self._graph_direction)
		graph.display_html(direction=direction, pad=pad, **kwargs)
		return graph.get_html(direction=direction, pad=pad, **kwargs)

	def __contains__(self, item):
		"""
		:param str item: key to a memory
		:rtype: bool
		"""
		return item in self.memories_dictionary

	def keys(self):
		return self._memories_dictionary.keys()

	@property
	def memories_dictionary(self):
		"""
		:rtype: dict[str,Memory]
		"""
		return self._memories_dictionary

	@property
	def memories(self):
		"""
		:rtype: dict[str,Memory]
		"""
		return self._memories_dictionary

	def freeze(self, memory=None, forever=False):
		"""
		:type memory: Memory or str
		:type forever: bool
		"""
		if memory is not None:
			memory_key, memory = self._get_key_and_memory(x=memory)
			memory.freeze(forever=forever)

		else:
			for memory in self.memories_dictionary.values():
				memory.freeze(forever=forever)

	def deep_freeze(self, memory=None):
		"""
		:type memory: Memory or str or NoneType
		"""
		self.freeze(memory=memory, forever=True)

	def unfreeze(self, memory=None):
		"""
		:type memory: Memory or str or NoneType
		"""
		if memory is not None:
			memory_key, memory = self._get_key_and_memory(x=memory)
			memory.unfreeze()
		else:
			for memory in self.memories_dictionary.values():
				memory.unfreeze()

	def _get_key_and_memory(self, x):
		"""
		:param str or Memory x: key to memory or the memory itself
		:rtype tuple(str, Memory)
		"""
		if isinstance(x, str):
			memory_key = x
			memory = self.memories_dictionary[x]
		else:
			memory = x
			memory_key = x.key
		return memory_key, memory

	def get_successors(self, memory):
		"""
		:param str or Memory memory: key to the memory you want the successor memories of
		:rtype: list[Memory]
		"""
		memory_key, _ = self._get_key_and_memory(memory)
		return [self._memories_dictionary[successor_key] for successor_key in self._successor_keys[memory_key]]

	def get_precursors(self, memory):
		"""
		:param str or Memory memory: key to the memory you want the precursor memories of
		:rtype: list[Memory]
		"""
		memory_key, _ = self._get_key_and_memory(memory)
		return [self._memories_dictionary[precursor_key] for precursor_key in self._precursor_keys[memory_key]]

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
		if isinstance(item, (float, int)):
			item = str(item)

		if item in self._memories_dictionary:
			memory = self._memories_dictionary[item]
			if self._safe:
				try:
					return deepcopy(memory.content)
				except MemoryRecursionError as e:
					message = str(f'could not deepcopy "{item}" because: {e}')
					warnings.warn(message)
					return memory.content
			else:
				return memory.content
		else:
			raise MissingMemoryError(f'Pensieve: the "{item}" memory does not exist!')

	def __setitem__(self, key, value):
		if isinstance(key, (int, float)):
			key = str(key)

		if isinstance(key, str):
			if (hasattr(value, '__call__') or callable(value)) and not key.endswith('_function'):
				self.store(key=key, function=value, evaluate=None)

			else:
				self.store(
					key=key, function=None, content=value, precursors=None, materialize=None, evaluate=None,
					metadata=None
				)
		elif isinstance(key, (list, tuple)):

			keys = key
			intermediary_node = f'intermediary_{self._num_intermediary_nodes+1}'
			self._num_intermediary_nodes += 1
			self[intermediary_node] = value
			self._memories_dictionary[intermediary_node]._label = ', '.join(keys)

			intermediary_value = self[intermediary_node]
			if len(intermediary_value) != len(keys):
				raise StoringError(f'{keys} has {len(keys)} elements but the result has {len(intermediary_value)} elements!')
			if isinstance(intermediary_value, dict):
				for x in keys:
					self.store(key=x, precursors=intermediary_node, function=lambda dictionary: dictionary[x])
			elif isinstance(intermediary_value, (list, tuple)):
				for i in range(len(keys)):
					self.store(key=keys[i], precursors=intermediary_node, function=lambda list_or_tuple: list_or_tuple[i])
			else:
				raise TypeError(f'result can only be of type list, tuple, or dict but it is of type {type(intermediary_value)}')

	def key_allowed(self, key):
		return key not in dir(self)

	def store(
			self, key, label=None, function=None, content=None, precursors=None,
			materialize=None, evaluate=None, metadata=None
	):
		"""
		:param str key: key to the new memory
		:param str or NoneType label:
		:param callable function: a function that runs on precursors and produces a new memory
		:param content: any object
		:param list[str] or NoneType precursors: key to precursor memories
		:param bool or NoneType materialize: if False, the memory does not store but only passes the results of the function
		:param bool or NoneType evaluate: if False the memory will not be evaluated
		:param dict or NoneType metadata: any information on the memory
		"""
		if evaluate is None:
			evaluate = self._evaluate

		if materialize is None:
			if function is None:
				materialize = True
			else:
				materialize = self._materialize

		if function is not None and content is not None:
			raise StoringError('Pensieve: at least one of function and content should be None!')
		elif function is None:
			if not materialize:
				raise StoringError('Pensieve: the content has to be materialized!')

			def function():
				return content
			precursors = []

		# Check inputs
		if not key:
			raise StoringError(f'Pensieve: no key provided for memory!')

		if not self.key_allowed(key=key):
			raise IllegalKeyError(f'{key} cannot be used as a memory key!')

		# if all function variables are in precursors this is not a standard pensieve function and needs to be converted
		function_arguments = get_function_arguments(function=function)
		if precursors is None:
			precursors = function_arguments

		if not isinstance(precursors, list):
			precursors = [precursors]

		missing_from_precursors = [name for name in function_arguments if name not in precursors]
		if len(missing_from_precursors) == 0 and len(precursors) > 1:
			pensieve_function = create_pensieve_function(function=function)
		else:
			pensieve_function = function

		number_of_precursors = len(precursors)
		precursors = remove_list_duplicates(precursors)
		if len(precursors) < number_of_precursors:
			warnings.warn('There are duplicates among precursors! They are removed but they may cause error later on!')

		# Check precursor states are known, i.e., precursor memories exist
		unknown_precursors = set(precursors).difference(set(self._memories_dictionary.keys()))
		if unknown_precursors:
			precursor_str = ', '.join([f'"{s}"' for s in unknown_precursors])
			raise UnknownPrecursorError(f'Pensieve: error adding "{key}": Unknown precursor memories: {precursor_str}')

		# make sure there is no loops
		for memory in precursors:
			ancestor_names = [ancestor.key for ancestor in self.get_ancestors(memory=memory)]
			if key in ancestor_names:
				raise MemoryRecursionError(f'Pensieve: "{key}" is an ancestor memory of its precursor: "{memory}"!')

		# Create or update memory
		precursor_memories = remove_list_duplicates([self._memories_dictionary[p] for p in precursors])

		if key in self._memories_dictionary:
			memory = self._memories_dictionary[key]
			if len(precursors) == 0:
				memory._precursors_hash = None

			memory.update(
				label=label,
				precursors=precursor_memories, function=pensieve_function,
				metadata=metadata, materialize=materialize,
				_original_function=function
			)

		else:
			memory = Memory(
				key=key, label=label, pensieve=self, safe=self._safe,
				precursors=precursor_memories, function=pensieve_function,
				metadata=metadata, materialize=materialize,
				_original_function=function, hash=self._do_hash, n_jobs=self._n_jobs
			)
			self._memories_dictionary[key] = memory

		if evaluate and materialize:
			memory = self.memories_dictionary[key]
			memory.evaluate()  # this will update the content if necessary

	def erase(self, memory):
		"""
		:param str or Memory memory: memory to be forgotten
		:return:
		"""
		memory_key, memory = self._get_key_and_memory(x=memory)
		del self._memories_dictionary[memory_key]
		for successor in self._successor_keys[memory_key]:
			self._precursor_keys[successor].remove(memory_key)
		del self._successor_keys[memory_key]

		for precursor in self._precursor_keys[memory_key]:
			self._successor_keys[precursor].remove(memory_key)
		del self._precursor_keys[memory_key]

	def __delitem__(self, key):
		self.erase(memory=key)

	def graphviz_str(self):
		dot_str = "strict digraph G { \n\t{\n "

		for memory in self._memories_dictionary.values():
			node_str = f'{memory.label}'
			dot_str += f'\t\t{node_str}\n'
		dot_str += '\t}\n'
		for memory in self._memories_dictionary.values():
			node_str = memory.graphviz_edges_str
			if node_str:
				dot_str += f"\t{node_str}\n"
		dot_str += "}"

		return dot_str

	def __repr__(self):
		return str(self)

	def __str__(self):
		if not len(self._memories_dictionary):
			return "<empty graph>"

		# Sort memories topologically
		def get_dependencies(n):
			return set(n.precursor_keys)

		to_be_topologically_sorted = {memory.key: get_dependencies(memory) for memory in self._memories_dictionary.values()}
		topologically_sorted = [l for g in toposort(to_be_topologically_sorted) for l in g]

		# Find longest strings so we can pad our strings to equal length later
		def get_precursors_str(n):
			return ', '.join(self._memories_dictionary[n].precursor_keys)

		data_to_print = [(get_precursors_str(n), n, self._memories_dictionary[n].is_stale) for n in topologically_sorted]
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

		if self._hide_ignored:
			memories_dictionary = {
				key: memory for key, memory in self.memories_dictionary.items()
				if memory._content_access_count > 0
			}
			successor_keys = {
				parent: [x for x in self._successor_keys[parent] if x in memories_dictionary]
				for parent in memories_dictionary.keys()
			}

		else:
			memories_dictionary = self.memories_dictionary
			successor_keys = self._successor_keys

		frozen_colour = '#deebf7'
		edge_frozen_colour = '#b8d4ed'

		node_colours = {
			name: '#f2f2f2' if not memory.is_frozen else frozen_colour
			for name, memory in self.memories_dictionary.items()
			if memory.is_stale or memory.is_frozen
		}

		frozen_edges = [
			(parent, child) for parent, children in successor_keys.items()
			for child in children
			if self.memories_dictionary[parent].is_frozen and self.memories_dictionary[parent].has_successors
		]

		edge_colours = {
			parent_child: edge_frozen_colour
			for parent_child in frozen_edges
		}

		return {
			'colour_scheme': 'pensieve2',
			'label': self._name,
			'label_url': 'https://pypi.org/project/pensieve/',
			'nodes': {key: memory.__graph_node__() for key, memory in memories_dictionary.items()},
			'edges': [
				(parent, child, {'style': {'line_width': self.memories_dictionary[parent].type_significance*5}})
				for parent, children in successor_keys.items() for child in children
			],
			'strict': True,
			'node_colours': node_colours,
			'edge_colours': edge_colours
		}

	def _get_ancestors(self, memory, memories_travelled=None):
		"""
		:type memory: Memory or str
		:type memories_travelled: list[Node] or None
		:rtype: list[Node]
		"""
		memories_travelled = memories_travelled or []
		memories_travelled.append(memory)
		parents = self.get_precursors(memory=memory)
		if len(parents) == 0:
			return []
		else:
			ancestors = []
			for parent in parents:
				if parent not in ancestors:
					ancestors.append(parent)

				if parent not in memories_travelled:
					parent_ancestors = self._get_ancestors(
						memory=parent, memories_travelled=memories_travelled
					)
					for ancestor in parent_ancestors:
						if ancestor not in ancestors:
							ancestors.append(ancestor)
			return ancestors

	def get_ancestors(self, memory):
		return self._get_ancestors(memory=memory, memories_travelled=[])

	@property
	def performance(self):
		"""
		:rtype: pandas.DataFrame
		"""
		result = self.function_durations.performance_summary
		result['total_evaluation_time'] = result.apply(
			lambda x: convert(delta=self.memories_dictionary[x['name']].total_time, to_unit=x['unit']),
			axis=1
		)
		result['precursor_evaluation_time'] = result['total_evaluation_time'] - result['mean_duration']

		# sizes = [{'name': name, 'type': memory.get_summary()} for name, memory in self.memories_dictionary.items()]
		return result

	@property
	def timestamps(self):
		"""
		:rtype: pandas.DataFrame
		"""
		return self.function_durations.timestamps

	@property
	def function_durations(self):
		"""
		:rtype: MeasurementSet
		"""
		return self._function_durations

	def decouple(self, key, prefix=None, suffix=None, precursors=None, separator='_', evaluate=None, materialize=None):
		"""
		decouples a dictionary memory into its items as new memories and returns the names of new memories
		:param str key: key of the original memory
		:param str or NoneType prefix: prefix for new children, if None, the original key will be used with a separator
		:param str or NoneType suffix: suffix to be added at the end of keys for children
		:param list[str] or str or NoneType precursors: other dependencies that are not automatically added but should
		be considered in case changes do not automatically make this memory stale
		:param str separator: separator to be used for creating keys for children
		:param NoneType or bool evaluate:
		:param NoneType or bool materialize:
		:rtype: list[str]
		"""
		keys = self[key].keys()
		if precursors is not None:
			if isinstance(precursors, str):
				precursors = [precursors]

		def create_getter(_child_key):
			def getter_function(x):
				return x[_child_key]
			return getter_function

		result = []
		for child_key in keys:
			if prefix is None:
				new_key = f'{key}{separator}{child_key}{suffix or ""}'
			else:
				new_key = f'{prefix}{child_key}{suffix or ""}'

			if precursors is None:
				self.store(
					key=new_key,
					precursors=key,
					function=lambda x: create_getter(child_key)(x),
					evaluate=evaluate,
					materialize=materialize
				)
			else:
				self.store(
					key=new_key,
					precursors=[key] + precursors,
					function=lambda x: create_getter(child_key)(x[key]),
					evaluate=evaluate,
					materialize=materialize
				)
			result.append(new_key)
		return result

	def get_contents(self):
		new_pensieve = self.__class__(
			safe=self._safe, function_durations=self._function_durations, warn_unsafe=False,
			hide_ignored=self._hide_ignored
		)

		for key, memory in self.memories_dictionary.items():
			new_pensieve._memories_dictionary[key] = memory.partial_copy()
		new_pensieve._precursor_keys = self._precursor_keys.copy()
		new_pensieve._successor_keys = self._successor_keys.copy()
		return new_pensieve
