from ..messages import single
from .component import Component

# only used for world control
class MinigameComponent(Component):
	def serialize(self, out, is_creation):
		pass

	@single
	def player_ready(self):
		pass
