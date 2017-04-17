from ..bitstream import c_bit, c_int, c_int64
from ..ldf import LDF
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
		self.driver_id = player.object_id
		player.char.vehicle_id = self.object.object_id
		player.char.display_tooltip(show=True, time=1000, id="", localize_params=LDF(), str_image_name="", str_text="Use /dismount to dismount.")

	def on_destruction(self):
		if self.driver_id != 0:
			self.object._v_server.game_objects[self.driver_id].char.vehicle_id = 0
			self.driver_id = 0

	def request_die(self, unknown_bool:bool=None, death_type:str=None, direction_relative_angle_xz:float=None, direction_relative_angle_y:float=None, direction_relative_force:float=None, kill_type:c_int=0, killer_id:c_int64=None, loot_owner_id:c_int64=None):
		#self.object.destructible.deal_damage(10000, self) # die permanently on crash
		self.object.call_later(3, self.object.destructible.resurrect)
