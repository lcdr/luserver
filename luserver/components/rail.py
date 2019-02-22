from typing import Optional

from bitstream import WriteStream
from ..game_object import Config, GameObject, Player
from .component import Component

class RailActivatorComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self._rail_path = set_vars.get("rail_path", "")
		self._rail_path_start = set_vars.get("rail_path_start", 0)

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.char.start_rail_movement(path_go_forward=self._rail_path_start == 0, loop_sound="", path_name=self._rail_path, path_start=self._rail_path_start, rail_activator_component_id=6, rail_activator=self.object, start_sound="", stop_sound="")
		player.char.set_rail_movement(path_go_forward=self._rail_path_start == 0, path_name=self._rail_path, path_start=self._rail_path_start)

		# possibly belongs in a script, newer scripts were removed so i can't tell
		player.char.set_flag(True, 2020)
