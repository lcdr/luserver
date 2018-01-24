from pyraknet.bitstream import c_bit, c_int64
from ..game_object import c_int, E, GameObject
from ..world import server
from .component import Component

class Comp108Component(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.comp_108 = self
		self._flags["driver_id"] = "driver_id_flag"
		self._flags["driver_id_flag"] = "comp108_main_flag"
		self.driver_id = 0

	def serialize(self, out, is_creation):
		out.write(c_bit(self.comp108_main_flag))
		if self.comp108_main_flag:
			out.write(c_bit(self.driver_id_flag))
			if self.driver_id_flag:
				out.write(c_int64(self.driver_id))
				self.driver_id_flag = False
			out.write(c_bit(False))
			out.write(c_bit(False))
			self.comp108_main_flag = False

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.char.mount(self.object)
		player.char.disp_tooltip("Use /dismount to dismount.")

	def on_destruction(self):
		if self.driver_id != 0:
			server.game_objects[self.driver_id].char.dismount()

	def request_die(self, unknown_bool:bool=E, death_type:str=E, direction_relative_angle_xz:float=E, direction_relative_angle_y:float=E, direction_relative_force:float=E, kill_type:c_int=0, killer:GameObject=E, loot_owner:GameObject=E):
		#self.object.destructible.deal_damage(10000, self) # die permanently on crash
		self.object.call_later(3, self.object.destructible.resurrect)
