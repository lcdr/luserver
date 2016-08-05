import asyncio
from ..bitstream import c_bit, c_float, c_int, c_int64

class Comp108Component:
	def __init__(self, comp_id):
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
		player.vehicle_id = self.object_id
		self._v_server.send_game_message(player.display_tooltip, show=True, time=1000, id="", localize_params={}, str_image_name="", str_text="Use /dismount to dismount.", address=player.address)

	def request_die(self, address, unknown_bool:c_bit=None, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_int=0, killer_id:c_int64=None, loot_owner_id:c_int64=None):
		#self.deal_damage(10000, self) # die permanently on crash
		asyncio.get_event_loop().call_later(3, lambda: self._v_server.send_game_message(self.resurrect, broadcast=True))
