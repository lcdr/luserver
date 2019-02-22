from bitstream import WriteStream
from ..game_object import single
from .component import Component

# only used for world control
class MinigameComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def player_ready(self) -> None:
		pass

	player_ready = single(player_ready)
	on_player_ready = player_ready
