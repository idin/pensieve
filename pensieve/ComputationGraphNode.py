from .NodeStyle import NodeStyle
from .EdgeStyle import EdgeStyle
from slytherin.collections import remove_list_duplicates
from copy import deepcopy
from memoria import Pickler, make_hash_sha256
import dill

class ComputationGraphNode():
	def __init__(
			self, name, function, graph, parents=None, on_disk=False, style=None, edge_style=None, style_transferable=True,
			safe=True,
	):
		"""
		:type name: str
		:type parents: list[ComputationGraphNode]
		:type graph: ComputationGraph
		:type function: function
		:type graph: ComputationGraph
		:type on_disk: bool
		:type style: NodeStyle or None
		:type input_edge_style: EdgeStyle
		:type output_edge_style: EdgeStyle
		:type safe: bool
		:param safe: when True only a copy of the value is returned to avoid mutating it from outside
		"""
		# make parents unique
		parents = parents or []
		self._name = name
		#self._parents = []
		#self._children = []
		self._graph = graph
		self._value = None
		self._style = None
		self._input_edge_style = None
		self._output_edge_style = None
		self._style_transferable = None
		self._safe = safe
		if self.name not in self.graph._child_names:
			self.graph._child_names[self.name] = []
		if self.name not in self.graph._parent_names:
			self.graph._parent_names[self.name] = []
		self._frozen = False
		self._stale = True
		self._function = None
		self._on_disk = on_disk

		self.update(
			parents, function, on_disk=on_disk, style=style, edge_style=edge_style,
			style_transferable=style_transferable
		)

	def __eq__(self, other):
		return isinstance(other, ComputationGraphNode) and self.name == other.name

	def __hash__(self):
		return hash(self.name)

	def __repr__(self):
		return f'ComputationGraphNode:{self.name}'

	def __getstate__(self):
		# fixes pickle and deepcopy
		new_dict = dict(self.__dict__)
		new_dict['_function'] = dill.dumps(obj=new_dict['_function'])
		return new_dict

	def __setstate__(self, state):
		# fixes pickle and deepcopy
		self.__dict__ = state
		try:
			self.__dict__['_function'] = dill.loads(str=self.__dict__['_function'])
		except:
			pass

	def save(self, path, echo=1):
		"""
		:type path: str
		"""
		echo = max(0, echo)
		graph = self._graph
		value = self._value
		stale = self._stale
		frozen = self._frozen
		self._graph = None
		if echo: print(f'GN saving node "{self.name}" ', end='')
		try:
			Pickler.save(path=path, obj=self, echo=echo-1)
			if echo: print('done!')
		except Exception as e:
			# If the value is hard to save, we save the node without the value
			# but we make the node stale so that
			# next time it is evaluated it recreates its value
			if echo: print(e, ' ', end='')
			self._value = None
			self._stale = True
			self._frozen = False
			Pickler.save(path=path, obj=self, echo=echo-1)
			if echo: print('done!')
		finally:
			self._graph = graph
			self._value = value
			self._stale = stale
			self._frozen = frozen


	@staticmethod
	def load(path, graph, echo=0):
		"""
		:type path: str
		:type graph: ComputationGraph
		:rtype: ComputationGraphNode
		"""
		echo = max(0, echo)
		node = Pickler.load(path=path, echo=echo)
		node._graph = graph
		return node

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
	def graph(self):
		"""
		:rtype: ComputationGraph
		"""
		return self._graph


	@property
	def name(self):
		return self._name

	@property
	def label(self):
		name = self.name.replace('__', '\n').replace('_', ' ')
		if self.is_stale and self.is_frozen:
			return f'"{name}\n(stale & frozen)"'
		elif self.is_stale and not self.is_frozen:
			return f'"{name}\n(stale)"'
		elif not self.is_stale and self.is_frozen:
			return f'"{name}\n(frozen)"'
		else:
			return f'"{name}"'

	@property
	def parent_names(self):
		"""
		:type: list[str]
		"""
		return list(self._graph._parent_names[self.name])

	@property
	def parents(self):
		return self.graph.get_parents(name=self.name)

	@property
	def has_parents(self):
		return len(self.parent_names) > 0

	@property
	def child_names(self):
		"""
		:type: list[str]
		"""
		return list(self._graph._child_names[self.name])

	@property
	def children(self):
		return self.graph.get_children(name=self.name)

	@property
	def has_children(self):
		return len(self.child_names) > 0

	def remove_child(self, child):
		if isinstance(child, str):
			self.graph._child_names[self.name].remove(child)
		else:
			self.graph._child_names[self.name].remove(child.name)

	############################################################## COMPUTATION

	def update(self, parents, function, on_disk, style=None, edge_style=None, echo=0, style_transferable=True):
		"""
		:type parents: list[ComputationGraphNode]
		:type function: function
		:type on_disk: bool
		:type style: NodeStyle
		:type echo:
		:return:
		"""
		# make parents unique:
		parents = parents or []
		parents = remove_list_duplicates(parents)
		echo = max(0, echo)
		if echo: print(f"GN Updating '{self.name}'")
		if self._on_disk and not on_disk:
			self._graph.hard_memory.delete(key=self.name)
		self._on_disk = on_disk

		if style is not None:
			if style is False:
				self._style = None
			else:
				self._style = style

		if edge_style is not None:
			if edge_style is False:
				self._input_edge_style = None
				self._output_edge_style = None
			else:
				self._input_edge_style = edge_style
				self._output_edge_style = edge_style
		self._style_transferable = style_transferable

		parent_names = [p.name for p in parents]

		removed_parent_names = [name for name in self.parent_names if name not in parent_names] # self.unique_parents.difference(parents)
		new_parent_names = [name for name in parent_names if name not in self.parent_names]# set(parents).difference(self._parents)
		#self._parents = parents

		self.graph._parent_names[self.name] = parent_names
		for parent_name in removed_parent_names:
			self.graph._child_names[parent_name].remove(self.name)
		for parent_name in new_parent_names:
			self.graph._child_names[parent_name].append(self.name)

		self._function = function
		self.mark_stale()

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, value):
		if self.is_frozen:
			raise RuntimeError('GN: You cannot change the value while the node is frozen!')

		# only mark children stale if the value changes
		if make_hash_sha256(value) != make_hash_sha256(self._value):
			for child in self.children:
				child.mark_stale()

		if self._on_disk:
			self._graph.hard_memory.save(obj=value, key=self.name, echo=1, text=self.name)
		else:
			self._value = value

	def mark_stale(self):
		self._stale = True

	def evaluate(self, echo=1):
		echo = max(0, echo)
		if not self.is_stale or self.is_frozen:
			return self.value

		parent_vals = {p.name: p.evaluate(echo) for p in self.parents}
		if echo: print(f"GN Evaluating '{self.name}'")

		self._stale = False

		if len(self.parent_names) == 0:
			self.value = self._function()
		elif len(self.parent_names) == 1:
			parent_val = list(parent_vals.values())[0]
			self.value = self._function(parent_val)
		else:
			inputs = GraphEvaluationInput(parent_vals)
			self.value = self._function(inputs)

		self._hash = make_hash_sha256(self.value)
		return self.value




	@property
	def graphviz_edges_str(self):
		if not self.has_parents:
			return self.label if not self.has_children else None
		else:
			edges = [
				f'{parent.label} -> {self.label} {str(self.get_edge_to_parent_style(parent=parent))}'
				for parent in self.parents
			]
			return '\n'.join(edges)

	############################################################## STYLE

	@property
	def parents_with_transferable_style(self):
		result = []
		for parent in self.parents:
			if parent._style_transferable:
				result.append(parent)
			elif len(parent.parents_with_transferable_style)>0:
				result.append(parent.parents_with_transferable_style[0])
		return result


	@property
	def inherited_style(self):
		"""
		:rtype: NodeStyle
		"""
		if self.has_parents:
			parents_with_style = [
				parent for parent in self.parents_with_transferable_style if parent.inherited_style is not None
			]
			if len(parents_with_style) > 0:
				parent_style = parents_with_style[0].inherited_style
			else:
				parent_style = None
		else:
			parent_style = None



		if self._style is None:
			return parent_style
		elif type(self._style) is not NodeStyle:
			raise TypeError(f'node.style of {self.name} is not NodeStyle! it is {type(self._style)}')
		else:
			return self._style.complement(parent_style)
	@property
	def style(self):
		if self.inherited_style is None:
			return self.graph.node_style
		else:
			return self.inherited_style.complement(self.graph.node_style)

	@property
	def inherited_output_edge_style(self):
		"""
		:rtype: EdgeStyle
		"""
		if self.has_parents:
			parents_with_edge_style = [parent for parent in self.parents if parent.inherited_output_edge_style is not None]
			if len(parents_with_edge_style) > 0:
				parent_output_edge_style = parents_with_edge_style[0].inherited_output_edge_style
			else:
				parent_output_edge_style = None
		else:
			parent_output_edge_style = None

		if self._output_edge_style is None:
			return parent_output_edge_style
		elif type(self._output_edge_style) is not EdgeStyle:
			raise TypeError('node._output_edge_style is not EdgeStyle')
		else:
			return self._output_edge_style.complement(parent_output_edge_style)

	def get_edge_to_parent_style(self, parent):
		if parent.inherited_output_edge_style is not None:
			return parent.inherited_output_edge_style.complement(self.graph.edge_style)

		else:
			return self.graph.edge_style

	@property
	def parent_edge_style(self):
		raise ValueError('should not use this')

	@parent_edge_style.setter
	def parent_edge_style(self, parent_edge_style):
		self._input_edge_style = parent_edge_style

	@property
	def child_edge_style(self):
		raise ValueError('should not be used')

	@child_edge_style.setter
	def child_edge_style(self, child_edge_style):
		self._output_edge_style = child_edge_style




class GraphEvaluationInput():
	def __init__(self, inputs):
		self.__dict__ = inputs

	def __getitem__(self, name):
		return self.__dict__[name]