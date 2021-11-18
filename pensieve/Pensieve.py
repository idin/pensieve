from ._PensieveWithoutDisplay import PensieveWithoutDisplay


class Pensieve(PensieveWithoutDisplay):
	def get_svg(self, direction=None, pad=None, **kwargs):
		"""
		:type direction: NoneType or str
		:type pad: NoneType or int or float
		:rtype: str
		"""
		return self.get_graph(direction=self.graph_direction).get_svg(direction=direction, pad=pad, **kwargs)

	def _repr_html_(self):
		return self.get_graph()._repr_html_()

	def get_html(self, direction=None, pad=None, **kwargs):
		return self.get_graph().get_html(direction=direction or self.graph_direction, pad=pad, **kwargs)

	"""
	def display_html(self, direction=None, pad=None, **kwargs):
		graph = self.get_graph(direction=self._graph_direction)
		graph.display_html(direction=direction, pad=pad, **kwargs)
		# return graph.get_html(direction=direction, pad=pad, **kwargs)
	
	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text('Pensieve')
		else:
			self.display(p=p)

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
	"""
