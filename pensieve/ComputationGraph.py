from toposort import toposort
from memoria import HardMemory, Pickler
import graphviz
from .NodeStyle import NodeStyle
from .EdgeStyle import EdgeStyle
from .ComputationGraphNode import ComputationGraphNode
from slytherin.collections import remove_list_duplicates
from revelio import make_dir
from interaction import ProgressBar
import os.path

class ComputationGraph():
	def __init__(self, echo=0, hard_memory_path='computation_graph', node_style=None, edge_style=None, on_disk=False, safe=True):
		"""
		:type echo:
		:type hard_memory_path: str
		:type node_style: NodeStyle or None
		:type safe: bool
		:param safe: when True the nodes are created as safe nodes
		"""
		echo = max(0, echo)
		self._echo = echo
		self._nodes = {}
		self._parent_names = {}
		self._child_names = {}
		self._hard_memory = None
		self._hard_memory_path = hard_memory_path
		self._safe = safe
		original_node_style = NodeStyle(
			colour='gray80',
			text_colour='deepskyblue2',
			fill_colour='gray95',
			text_size=8,
			font='helvetica',
			shape='egg',
			style='filled'

		)
		if node_style is None:
			node_style = original_node_style
		else:
			node_style = node_style.complement(original_node_style)

		self._node_style = node_style

		original_edge_style = EdgeStyle(
			colour='grey60',
			arrow_size=0.5
		)
		if edge_style is None:
			edge_style = original_edge_style
		else:
			edge_style = edge_style.complement(original_edge_style)

		self._edge_style = edge_style
		self._on_disk = on_disk

	def save(self, dir, echo=2):
		echo = max(0, echo)
		make_dir(path=dir, ignore_if_exists=True)
		old_nodes = self.nodes
		new_nodes = {}
		for name, node in old_nodes.items():
			path = os.path.join(dir, f'node_{name}.pickle')
			node.save(path=path, echo=echo-1)
			new_nodes[name] = path
		graph_path = os.path.join(dir, 'graph.pickle')
		self._nodes = new_nodes
		Pickler.save(path=graph_path, obj=self)
		self._nodes = old_nodes

	@staticmethod
	def load(dir, echo=1):
		"""
		:type dir: str
		:rtype: ComputationGraph
		"""
		graph = Pickler.load(path=os.path.join(dir, 'graph.pickle'), echo=echo)
		paths = graph._nodes
		graph._nodes = {}
		for name, path in paths.items():
			graph._nodes[name] = ComputationGraphNode.load(path=path, graph=graph, echo=echo)
		return graph

	@property
	def nodes(self):
		"""
		:rtype: dict[str,ComputationGraphNode]
		"""
		return self._nodes

	def freeze(self, node):
		"""
		:type node: ComputationGraphNode or str
		"""
		if isinstance(node, str):
			node_name = node
		else:
			node_name = node.name
		self.nodes[node_name].freeze()

	def unfreeze(self, node):
		"""
		:type node: ComputationGraphNode or str
		"""
		if isinstance(node, str):
			node_name = node
		else:
			node_name = node.name
		self.nodes[node_name].unfreeze()


	@property
	def node_style(self):
		"""
		:rtype: NodeStyle 
		"""
		return self._node_style

	def get_children(self, name):
		return [self._nodes[child_name] for child_name in self._child_names[name]]

	def get_parents(self, name):
		return [self._nodes[parent_name] for parent_name in self._parent_names[name]]

	@property
	def edge_style(self):
		"""
		:rtype: EdgeStyle
		"""
		return self._edge_style

	def __getitem__(self, item):
		if item in self._nodes:
			node = self._nodes[item]
			result = node.evaluate(self._echo)
			return result
		else:
			try:
				return super().__getitem__(item)
			except:
				raise AttributeError(item)



	def __getattr__(self, item):
		return self.__getitem__(item=item)

	def __getstate__(self):
		# fixes pickle and deepcopy
		return self.__dict__

	def __setstate__(self, state):
		# fixes pickle and deepcopy
		self.__dict__ = state

	@property
	def hard_memory(self):
		"""
		:rtype: HardMemory
		"""
		return self._hard_memory


	def add(
			self, name, function=None, obj=None, parents=None, evaluate=True, on_disk=False, node_style=None, edge_style=None,
			style_transferable=True
	):
		"""
		:type name: str
		:type parents: list[str]
		:type function: function
		:type evaluate: bool
		:type on_disk: bool
		:type node_style: NodeStyle or None
		"""
		if function is not None and obj is not None: raise ValueError('CG at least one of function and obj should be None!')
		if function is None: function = lambda: obj
		# Check inputs
		if not name:
			raise ValueError(f"Please specify a name for this node")
		if node_style is not None and type(node_style) is not NodeStyle:
			raise TypeError(f'node_style is {type(node_style)}')
		if edge_style is not None and type(edge_style) is not EdgeStyle:
			raise TypeError(f'edge_style is {type(edge_style)}')


		parents = parents or []
		parents = remove_list_duplicates(parents)

		if on_disk and self.hard_memory is None:
			self._hard_memory = HardMemory(path=self._hard_memory_path, log_access=True)

		# Check parent states are known
		unknown_states = set(parents).difference(set(self._nodes.keys()))
		if unknown_states:
			states_str = ', '.join([f"'{s}'" for s in unknown_states])
			raise KeyError(f"Error adding '{name}': Unknown parent state(s) {states_str}")

		# Create or update node

		parent_nodes = remove_list_duplicates([self._nodes[p] for p in parents])


		if name in self._nodes:
			node = self._nodes[name]
			node.update(
				parents=parent_nodes, function=function, on_disk=on_disk, style=node_style, edge_style=edge_style, echo=self._echo,
				style_transferable=style_transferable
			)
		else:
			if self._echo: print(f"CG Creating node '{name}'")
			node = ComputationGraphNode(
				name=name, parents=parent_nodes, function=function, graph=self, on_disk=on_disk, style=node_style, edge_style=edge_style,
				style_transferable=style_transferable, safe=self._safe
			)
			self._nodes[name] = node

		if evaluate:
			node = self._nodes[name]
			node.evaluate(self._echo)


	def delete(self, name):
		del self._nodes[name]



	def graphviz_str(self):

		dot_str = "strict digraph G { \n\t{\n " # {{node [margin={self.margin} fontcolor={self.font_colour} fontsize={self.font_size} width={self.width} shape={self.shape} style={self.style}] }}

		for n in self._nodes.values():
			node_str = f'{n.label} {n.style}'
			dot_str += f'\t\t{node_str}\n'
		dot_str += '\t}\n'
		for n in self._nodes.values():
			node_str = n.graphviz_edges_str
			if node_str:
				dot_str += f"\t{node_str}\n"
		dot_str += "}"

		return dot_str


	def __str__(self):
		if not len(self._nodes):
			return "<empty graph>"

		# Sort nodes topologically
		get_dependencies = lambda n: set(n.parent_names)
		toposort_in = { node.name: get_dependencies(node) for node in self._nodes.values() }
		toposorted = [l for g in toposort(toposort_in) for l in g]

		# Find longest strings so we can pad our strings to equal length later
		get_parents_str = lambda n: ', '.join(self._nodes[n].parent_names)
		data_to_print = [(get_parents_str(n), n, self._nodes[n].is_stale) for n in toposorted]
		longest_parents_str = max([len(d[0]) for d in data_to_print])
		longest_node_name = max([len(d[1]) for d in data_to_print])

		# Build output str in format: "[parents] --> node" along with an indicate of stale-ness
		result_str = ""
		for data in data_to_print:
			lside = data[0].rjust(longest_parents_str)
			rside = data[1].ljust(longest_node_name)
			stale_indic = " (stale)" if data[2] else ""
			result_str += f"{lside} --> {rside}{stale_indic}\n"
		result_str = result_str.rstrip('\n')
		return result_str

	def render(self):
		return graphviz.Source(self.graphviz_str())

class Snapshot:
	def __init__(self, graph):
		"""
		:type graph: ComputationGraph
		"""
		self._graphviz_str = graph.graphviz_str()

	def render(self):
		return graphviz.Source(self._graphviz_str)



