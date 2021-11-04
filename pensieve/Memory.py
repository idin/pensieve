from .EvaluationInput import EvaluationInput
from .get_type import get_type
from .get_schedule import get_schedule

from slytherin.collections import remove_list_duplicates
from slytherin import get_size
from memoria import hash_object
from chronometry import Timer
from disk import Path
from joblib import delayed
from chronometry.progress import ProgressBar
from pandas import DataFrame, Series
from random import random

import dill
import pickle
from inspect import getsource as get_source


class Memory:
	def __init__(
			self, key, pensieve, function, _original_function,
			label=None, precursors=None, safe=True, metadata=False, materialize=True,
			_update=True, _stale=True, hash=True, n_jobs=1
	):
		"""
		:param str key: unique name/identifier of the memory
		:param Pensieve pensieve: the pensieve this memory belongs to
		:param callable function: a function to be called on precursor memories
		:param list[Memory] or NoneType precursors: precursor memories to this memory
		:param bool safe: when True only a copy of the content is returned to avoid mutating it from outside
		:param dict metadata: an optional dictionary that carries meta data about this memory
		:param bool materialize: when False, memory runs the function when it needs the content, rather than keeping it
		:param bool _update: if True the precursors will be updated
		:param bool _stale:
		"""
		# make precursors unique
		precursors = precursors or []
		self._key = key
		self._label = label
		self._pensieve = pensieve
		self._content = None
		self._materialize = materialize
		self._safe = safe
		if self.pensieve is not None:
			if self.key not in self.pensieve._successor_keys:
				self.pensieve._successor_keys[self.key] = []
			if self.key not in self.pensieve._precursor_keys:
				self.pensieve._precursor_keys[self.key] = []
		self._frozen = False
		self._deep_freezed = False
		self._stale = _stale
		self._function = function
		self._original_function = _original_function
		self._metadata = metadata or {}

		self._total_time = None

		self._size = None
		self._precursors_hash = None
		self._content_type = None
		self._content_access_count = 0
		self._do_hash = hash
		self._n_jobs = n_jobs
		if self.pensieve and self.pensieve.backup_memory_directory:
			self._backup_directory = self.pensieve.backup_memory_directory.make_dir(name=self.key, ignore_if_exists=True)
		else:
			self._backup_directory = None

		if _update:
			self.update(precursors=precursors, function=function, _original_function=_original_function)

	__PARAMS__ = [
		'key', 'label', 'materialize', 'safe', 'frozen', 'deep_freezed', 'stale', 'metadata', 'total_time', 'size',
		'precursors_hash', 'content_type', 'content_access_count', 'backup_directory'
	]

	@property
	def num_threads(self):
		return self.pensieve._num_threads

	def clean_copy(self, include_function=False, stale=False, update=False):

		result = self.__class__(
			key=self.key, pensieve=None,
			function=self._function if include_function else None,
			precursors=None,
			safe=self._safe, metadata=self._metadata.copy(),
			materialize=self._materialize, _update=update, _stale=stale
		)
		return result

	def partial_copy(self, include_function=False, stale=False, update=False, include_precursor_hash=True):
		result = self.clean_copy(include_function=include_function, stale=stale, update=update)
		result._content = self._content
		result._content = self._content
		result._frozen = self._frozen
		result._total_time = self._total_time
		result._size = self._size
		result._precursors_hash = self._precursors_hash if include_precursor_hash else None
		result._content_type = self._content_type
		result._content_access_count = self._content_access_count
		return result

	def __hashkey__(self):
		return self.__class__.__name__, self.parameters, self.precursor_keys

	@property
	def parameters(self):
		return {param: getattr(self, f'_{param}') for param in self.__PARAMS__}

	def __getstate__(self):
		"""
		:rtype: dict
		"""
		stale = self._stale
		try:
			function_dump = dill.dumps(obj=self._function)
		except RecursionError as e:
			print(f'\nrecursion error during the dill.dumping of the "{self.key}" memory \n\n')
			raise e

		state = {
			'parameters': self.parameters,
			'function': function_dump
		}

		if not stale:
			try:
				state['serialized'] = pickle.dumps(obj=self._content, protocol=pickle.HIGHEST_PROTOCOL)
				state['serialized_by'] = 'pickle'
			except:
				try:
					state['serialized'] = dill.dumps(obj=self._content, protocol=dill.HIGHEST_PROTOCOL)
					state['serialized_by'] = 'dill'
				except:
					state['serialized_by'] = None
		else:
			state['serialized_by'] = None

		return state

	@classmethod
	def _backward_compatible_from_state(cls, state):
		memory = Memory(
			key=state['key'],
			function=dill.loads(str=state['function']),
			pensieve=None,
			precursors=None,
			safe=state['safe'],
			metadata=state['meta_data'],
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
		memory._elapsed_seconds = state['elapsed_seconds']
		if memory._content:
			memory._content_type = get_type(memory._content)
		return memory

	def __setstate__(self, state):
		"""
		:type state: dict
		"""
		parameters = state['parameters']
		for name, value in parameters.items():
			setattr(self, f'_{name}', value)
		if self._stale:
			self._content = None
			self._precursors_hash = None
		else:
			if state['serialized_by'] == 'dill':
				self._content = dill.loads(str=state['serialized'])

			elif state['serialized_by'] == 'pickle':
				self._content = pickle.loads(state['serialized'])

			else:
				self._stale = True
				self._content = None
				self._precursors_hash = None
		self._function = dill.loads(str=state['function'])
		self._pensieve = None

	@property
	def backup_directory(self):
		"""
		:rtype: Path or NoneType
		"""
		return self._backup_directory

	def save(self, path):
		"""
		:type path: str or Path
		"""
		path = Path(string=path)
		path.make_dir()
		parameters = {param: getattr(self, f'_{param}') for param in self.__PARAMS__}
		try:
			(path + 'content.pensieve').save(obj=self._content)
		except:
			parameters['stale'] = True
		(path + 'parameters.pensieve').save(obj=parameters)
		(path + 'function.pensieve').save(obj=self._function, method='dill')

	@classmethod
	def load(cls, path, pensieve):
		path = Path(string=path)
		parameters = (path + 'parameters.pensieve').load()
		function = (path + 'function.pensieve').load(method='dill')
		memory = cls(
			pensieve=pensieve, function=function, precursors=None,
			key=parameters['key'], _update=False
		)
		for name, value in parameters.items():
			setattr(memory, f'_{name}', value)
		memory._function = function
		try:
			memory._content = (path + 'content.pensieve').load()
		except:
			memory._content = None
			memory._stale = True
		return memory

	def get_summary(self):
		result = {
			'key': self.key,
			'content_type': self._content_type,
			'materialized': self._materialize,
			'frozen': self._frozen,
			'evaluation_time': self.evaluation_time,
			'total_time': self.total_time,
			'size': self.size,
			'precursors_hash': self._precursors_hash,
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
			result += get_size(self._precursors_hash, exclude_objects=[self._pensieve])
			result += get_size(self._content_type, exclude_objects=[self._pensieve])
			result += get_size(self._safe, exclude_objects=[self._pensieve])
			result += get_size(self._frozen, exclude_objects=[self._pensieve])
			result += get_size(self._stale, exclude_objects=[self._pensieve])
			result += get_size(self._function, exclude_objects=[self._pensieve])
			result += get_size(self._metadata, exclude_objects=[self._pensieve])
			result += get_size(result)
			self._size = result
		return self._size

	@property
	def evaluation_time(self):
		if self.key in self.pensieve.function_durations.measurements:
			return self.pensieve.function_durations.measurements[self.key].mean_duration
		else:
			return None

	@property
	def total_time(self):
		if self._total_time is None:
			if len(self.precursor_keys) == 0:
				self._total_time = self.evaluation_time
			else:
				self._total_time = self.evaluation_time
				for precursor in self.precursors:
					self._total_time += precursor.total_time
		return self._total_time

	@property
	def speed(self):
		evaluation_time = self.evaluation_time
		if evaluation_time is not None:
			return self.size / evaluation_time
		else:
			return None

	def display(self, p=None):
		print(self._get_dependency_summary())
		if p is None:
			try:
				from IPython.core.display import display
				display(self.content)
			except ImportError:
				print(self.content)
		else:
			p.pretty(self.content)

	def _get_dependency_summary(self):
		precursor_keys = self.precursor_keys
		successor_keys = self.successor_keys
		if len(precursor_keys) > 0:
			precursors = 'precursors: ' + ', '.join(precursor_keys)
		else:
			precursors = 'no precursors'

		if len(successor_keys) > 0:
			successors = 'successors: ' + ', '.join(successor_keys)
		else:
			successors = 'no successors'
		return f'{precursors}\n{successors}'

	def __sizeof__(self):
		return self.size

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		if self.key != other.key:
			return False

		all_keys = set(self.precursor_keys).union(other.precursor_keys)
		if len(all_keys) > len(self.precursor_keys) or len(all_keys) > len(other.precursor_keys):
			return False

		if self.content != other.content:
			return False

		return True

	def __hash__(self):
		return hash(self.key)

	def __repr__(self):
		return f'Memory:{self.key}'

	@property
	def is_frozen(self):
		return self._frozen

	@property
	def is_stale(self):
		return self._stale

	def freeze(self, forever=False):
		self._frozen = True
		self._deep_freezed = forever
		if forever:
			self._function = None

	def deep_freeze(self):
		self.freeze(forever=True)

	def unfreeze(self):
		if not self._deep_freezed:
			self._frozen = False
			if self._stale:
				self.mark_stale()
		else:
			print(f'{self.key} is deep-freezed and cannot be thawed!')

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
		output = self._label or self.key.replace('__', '\n').replace('_', ' ')

		if self._deep_freezed:
			frozen_label = 'deep-freezed'
		else:
			frozen_label = 'frozen'

		if self.is_stale and self.is_frozen:
			output += f'\n( stale & {frozen_label} )'
		elif self.is_stale and not self.is_frozen:
			output += '\n( stale )'
		elif not self.is_stale and self.is_frozen:
			output += f'\n( {frozen_label} )'
		else:
			output += f'\n{self._content_type}'

		return output

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
		"""
		:rtype: list[Memory]
		"""
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

	def update(self, precursors, function, _original_function, label=None, metadata=None, materialize=None):
		"""
		:type precursors: list[Memory]
		:type function: callable
		:type metadata: NoneType or dict
		:type materialize: bool or NoneType
		"""
		# make precursors unique:
		if self.is_frozen:
			raise MemoryError(f'{self.key} is frozen. You cannot change a frozen memory!')

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
		self._original_function = _original_function
		self.mark_stale()

		if metadata is not None:
			self._metadata = metadata
		if materialize is not None:
			self._materialize = materialize

		if label is not None:
			self._label = label

	def evaluate(self):
		_ = self.content

	@property
	def stale_precursors(self):
		"""
		:rtype: list[Memory]
		"""
		return [precursor for precursor in self.precursors if precursor.is_stale]

	def _get_stale_dependencies(self, unique=False):
		"""
		:rtype: list[Memory]
		"""
		dependencies = []
		for precursor in self.stale_precursors:
			dependencies.append(precursor)
			dependencies += precursor._get_stale_dependencies(unique=False)

		if unique:
			unique_dependencies = []
			for dependency in dependencies:
				if dependency not in unique_dependencies:
					unique_dependencies.append(dependency)
			return unique_dependencies
		else:
			return dependencies

	@property
	def stale_dependencies(self):
		"""
		:rtype: list[Memory]
		"""
		return self._get_stale_dependencies(unique=True)

	def get_update_schedule(self):
		"""
		:rtype: list[list[Memory]]
		"""
		jobs = self.stale_dependencies
		jobs.reverse()
		return get_schedule(jobs=jobs)

	@property
	def type_significance(self):
		if isinstance(self._content, (DataFrame, Series, list, dict, set)):
			return 2
		else:
			return 1

	@property
	def content(self):
		if not self._materialize:
			self.set_content(content=None, precursors_hash=None)
			content, precursors_hash = self.get_content_and_hash()

		elif self.is_frozen or not self.is_stale:
			content = self._content

		else:
			content, precursors_hash = self.get_content_and_hash()
			self.set_content(content=content, precursors_hash=precursors_hash)
			content = self._content

		return content

	def set_content(self, content, precursors_hash):
		if self.is_frozen:
			raise MemoryError(f'{self.key} is frozen. You cannot change a frozen memory!')
		self._content = content
		self._stale = False
		self._precursors_hash = precursors_hash

	@property
	def backup_content_pickle_path(self):
		"""
		:rtype: Path or NoneType
		"""
		if self.backup_directory:
			return (self.backup_directory + f'{self.key}_content.pickle')
		else:
			return None

	@property
	def backup_content_dill_path(self):
		"""
		:rtype: Path or NoneType
		"""
		if self.backup_directory:
			return (self.backup_directory + f'{self.key}_content.dill')
		else:
			return None

	def backup_content_exists(self):
		return self.backup_content_pickle_path.exists() or self.backup_content_dill_path.exists()

	@property
	def backup_precursors_hash_path(self):
		"""
		:rtype: Path or NoneType
		"""
		if self.backup_directory:
			return (self.backup_directory + f'{self.key}_hash.pickle')
		else:
			return None

	@property
	def backup_content(self):
		if self.backup_directory:
			if self.backup_content_pickle_path.exists():
				return self.backup_content_pickle_path.load(method='pickle', echo=0)
			elif self.backup_content_dill_path.exists():
				return self.backup_content_dill_path.load(method='dill', echo=0)
			else:
				return None
		else:
			return None

	@backup_content.setter
	def backup_content(self, content):
		if self.backup_directory:
			try:
				self.backup_content_pickle_path.save(obj=content, method='pickle', echo=0)
			except:
				if self.backup_content_pickle_path.exists():
					self.backup_content_pickle_path.delete()
				try:
					self.backup_content_dill_path.save(obj=content, method='dill', echo=0)
				except Exception as e:
					if self.backup_content_dill_path.exists():
						self.backup_content_dill_path.delete()

	@property
	def backup_precursors_hash(self):
		if self.backup_directory and self.backup_precursors_hash_path.exists():
			return self.backup_precursors_hash_path.load(method='pickle', echo=0)

		else:
			return None

	@backup_precursors_hash.setter
	def backup_precursors_hash(self, precursors_hash):
		if self.backup_directory:
			self.backup_precursors_hash_path.save(obj=precursors_hash, method='pickle', echo=0)

	def mark_stale(self):
		if self._materialize:
			self._stale = True
		self._size = None
		for successor in self.successors:
			successor.mark_stale()

	def hash_object(self, obj):
		if self._do_hash:
			return hash_object(obj=obj, n_jobs=self._n_jobs, base=64)
		else:
			return str(random())

	def get_content_and_hash(self):
		if self.num_threads == 1:
			precursor_keys_to_contents = {p.key: p.content for p in self.precursors}
		else:
			def get_content(p):
				return p.content

			precursors = self.precursors

			schedule = self.get_update_schedule()

			progress_bar = ProgressBar(
				total=sum([len(schedule_round) for schedule_round in schedule]),
				echo=self.pensieve._echo
			)

			progress_amount = 0
			for schedule_round in schedule:
				progress_bar.show(amount=progress_amount, text=f'updating {len(schedule_round)} memories')
				self.pensieve.processor(delayed(get_content)(job) for job in schedule_round)
				progress_amount += len(schedule_round)
			if progress_amount > 0:
				progress_bar.show(amount=progress_amount, text=f'{self.key} updated!')

			contents = self.pensieve.processor(delayed(get_content)(p) for p in precursors)
			keys = [precursor.key for precursor in precursors]
			precursor_keys_to_contents = {key: content for key, content in zip(keys, contents)}

		if len(self.precursor_keys) == 0:
			new_hash = self.hash_object(get_source(self._original_function))

			if new_hash == self._precursors_hash and self._materialize:
				new_content = self._content
			elif self.backup_directory and new_hash == self.backup_precursors_hash and self.backup_content_exists():
				new_content = self.backup_content

			else:
				timer = Timer(start_now=True, unit='timedelta')
				new_content = self._function()
				timer.stop()
				self.pensieve.function_durations.add_measurement(name=self.key, timer=timer)

		elif len(self.precursor_keys) == 1:
			precursor_content = list(precursor_keys_to_contents.values())[0]
			new_hash = self.hash_object((get_source(self._original_function), precursor_keys_to_contents))
			if new_hash == self._precursors_hash and self._materialize:
				new_content = self._content
			elif self.backup_directory and new_hash == self.backup_precursors_hash and self.backup_content_exists():
				new_content = self.backup_content

			else:
				timer = Timer(start_now=True, unit='timedelta')
				new_content = self._function(precursor_content)
				timer.stop()
				self.pensieve.function_durations.add_measurement(name=self.key, timer=timer)

		else:
			inputs = EvaluationInput(inputs=precursor_keys_to_contents)
			new_hash = self.hash_object((get_source(self._original_function), precursor_keys_to_contents))
			if new_hash == self._precursors_hash and self._materialize:
				new_content = self._content
			elif self.backup_directory and new_hash == self.backup_precursors_hash and self.backup_content_exists():
				new_content = self.backup_content
			else:
				timer = Timer(start_now=True, unit='timedelta')
				new_content = self._function(inputs.originals)

				timer.stop()
				self.pensieve.function_durations.add_measurement(name=self.key, timer=timer)

		self._content_type = get_type(new_content)

		self._content_access_count += 1
		if self.backup_directory and new_hash != self.backup_precursors_hash:
			self.backup_content = new_content
			self.backup_precursors_hash = new_hash
		return new_content, new_hash

	@property
	def hash(self):
		"""
		:rtype: str
		"""
		return self._precursors_hash

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
