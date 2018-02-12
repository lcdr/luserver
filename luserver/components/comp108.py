from typing import cast, Optional

from pyraknet.bitstream import c_bit, c_int64, WriteStream
from ..game_object import c_int, Config, DestructibleObject, EB, EF, ES, EO, EP, GameObject, Player
from ..world import server
from .component import Component

class Comp108Component(Component):
	object: DestructibleObject

	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.comp_108 = self
		self._flags["driver_id"] = "driver_id_flag"
		self._flags["driver_id_flag"] = "comp108_main_flag"
		self.driver_id = 0

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("comp108_main_flag", out):
			if self.flag("driver_id_flag", out):
				out.write(c_int64(self.driver_id))
			out.write(c_bit(False))
			out.write(c_bit(False))

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.char.mount(self.object)
		player.char.ui.disp_tooltip("Use /dismount to dismount.")

	def on_destruction(self) -> None:
		if self.driver_id != 0:
			cast(Player, server.game_objects[self.driver_id]).char.dismount()

	def on_request_die(self, unknown_bool:bool=EB, death_type:str=ES, direction_relative_angle_xz:float=EF, direction_relative_angle_y:float=EF, direction_relative_force:float=EF, kill_type:c_int=0, killer:GameObject=EO, loot_owner:Player=EP) -> None:
		#self.object.destructible.deal_damage(10000, self) # die permanently on crash
		self.object.call_later(3, self.object.destructible.resurrect)
