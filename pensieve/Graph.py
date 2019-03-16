from toposort import toposort
import graphviz
from .NodeStyle import NodeStyle
from .EdgeStyle import EdgeStyle
from .ComputationGraphNode import ComputationGraphNode
from memoria import HardMemory


class Graph:
	def __init__(self, echo=0, node_style=None, edge_style=None):
		"""
		:type echo: int
		:type node_style: NodeStyle or None
		"""
		echo = max(0, echo)
		self._echo = echo
		self._nodes = {}
		self._hard_memory = None
		original_node_style = NodeStyle(
			colour='gray80',
			text_colour='deepskyblue2',
			fill_colour='gray95',
			text_size=10,
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

	@property
	def node_style(self):
		"""
		:rtype: NodeStyle
		"""
		return self._node_style

	@property
	def edge_style(self):
		"""
		:rtype: EdgeStyle
		"""
		return self._edge_style

	def __getitem__(self, item):
		node = self._nodes[item]
		result = node.evaluate(self._echo)
		return result

	def __getattr__(self, item):
		return self.__getitem__(item=item)

	@property
	def hard_memory(self):
		"""
		:rtype: HardMemory
		"""
		return self._hard_memory


	def add(self, name, parents, function, evaluate=True, on_disk=False, node_style=None):
		"""
		:type name: str
		:type parents: list[str]
		:type function: function
		:type evaluate: bool
		:type on_disk: bool
		:type node_style: NodeStyle or None
		"""

		# Check inputs
		if not name:
			raise ValueError(f"Please specify a name for this node")
		parents = parents or []
		if on_disk and self.hard_memory is None:
			self._hard_memory = HardMemory(path=self._hard_memory_path, log_access=True)

		# Check parent states are known
		unknown_states = set(parents).difference(set(self._nodes.keys()))
		if unknown_states:
			states_str = ', '.join([f"'{s}'" for s in unknown_states])
			raise KeyError(f"Error adding '{name}': Unknown parent state(s) {states_str}")

		# Create or update node
		parent_nodes = set([self._nodes[p] for p in parents])
		if name in self._nodes:
			node = self._nodes[name]
			node.update(parent_nodes, function, on_disk=on_disk, style=node_style, echo=self._echo)
		else:
			if self._echo: print(f"CG Creating node '{name}'")
			node = ComputationGraphNode(name, parent_nodes, function, graph=self, on_disk=on_disk, style=node_style)
			self._nodes[name] = node

		if evaluate:
			node = self._nodes[name]
			node.evaluate(self._echo)


	def delete(self, name):
		del self._nodes[name]



	def graphviz_str(self):
		def node_to_graphviz(n):
			"""
			:type n: ComputationGraphNode
			:rtype: str
			"""
			#node_name = f"\"{n.name}\""
			node_name_and_status = f"\"{n.name_and_status}\""
			parent_names = [f"\"{p.name_and_status}\"" for p in n.parent_names]
			if not len(parent_names):
				return node_name_and_status if not len(n.child_names) else None
			if len(parent_names) == 1:
				return f"{parent_names[0]} -> {node_name_and_status} {str(self.edge_style)}"
			else:
				return f"{{ {' '.join(parent_names)} }} -> {node_name_and_status} {str(self.edge_style)}"

		dot_str = "strict digraph G { \n\t{\n " # {{node [margin={self.margin} fontcolor={self.font_colour} fontsize={self.font_size} width={self.width} shape={self.shape} style={self.style}] }}

		for n in self._nodes.values():
			node_str = f'"{n.name_and_status}" {n.style}'
			dot_str += f'\t\t{node_str}\n'
		dot_str += '\t}\n'
		for n in self._nodes.values():
			node_str = node_to_graphviz(n)
			if node_str:
				dot_str += f"\t{node_str}\n"
		dot_str += "}"

		return dot_str


	def __str__(self):
		if not len(self._nodes):
			return "<empty graph>"

		# Sort nodes topologically
		get_dependencies = lambda n: set([c.name for c in n.parent_names])
		toposort_in = { node.name: get_dependencies(node) for node in self._nodes.values() }
		toposorted = [l for g in toposort(toposort_in) for l in g]

		# Find longest strings so we can pad our strings to equal length later
		get_parents_str = lambda n: ', '.join([p.name for p in self._nodes[n].parent_names])
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



