from ._PensieveWithoutDisplay import PensieveWithoutDisplay


class Pensieve(PensieveWithoutDisplay):
	def get_svg(self, direction=None, pad=None, **kwargs):
		"""
		:type direction: NoneType or str
		:type pad: NoneType or int or float
		:rtype: str
		"""
		direction = direction or self._graph_direction

		return self.get_graph(direction=direction).get_svg(direction=direction, pad=pad, **kwargs)

	def _repr_html_(self):
		return self.get_graph()._repr_html_()

	def get_html(self, direction=None, pad=None, **kwargs):
		"""
		:type direction: NoneType or str
		:type pad: NoneType or int or float
		:rtype: str
		"""
		direction = direction or self._graph_direction
		return self.get_graph().get_html(direction=direction, pad=pad, **kwargs)
