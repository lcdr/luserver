from pyraknet.bitstream import WriteStream
from ..game_object import single
from .component import Component

# only used for world control
class MinigameComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	@single
	def player_ready(self) -> None:
		pass
