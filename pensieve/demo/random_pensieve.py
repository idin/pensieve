from ..ProtectedPensieve import Pensieve

from random import random

def _neural_network(layers, connection_probability=0.5)
	pensieve = Pensieve()
	if len(layers) == 0:
		return pensieve

	# first layer
	for node_index in range(layers[0]):
		pensieve[f'1_{node_index+1}'] = node_index

	# mid layers
	for layer_number_minus_1, layer in enumerate(layers[1:]):
		parents_layer = layers[layer_number_minus_1]
		for node_index in range(layer):
			# choose parents
			parents = []
