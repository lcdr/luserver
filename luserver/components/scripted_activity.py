import asyncio

from pyraknet.bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..game_object import GameObject
from ..world import server
from ..ldf import LDF
from ..messages import broadcast, single
from .component import Component

class ScriptedActivityComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.scripted_activity = self
		self._flags["activity_values"] = "activity_flag"
		self.activity_values = {}
		self.activity_id = comp_id
		if "transfer_world_id" in set_vars:
			self.transfer_world_id = set_vars["transfer_world_id"]
		elif self.activity_id in server.db.activities:
			activity = server.db.activities[self.activity_id]
			self.transfer_world_id = activity[0]
		else:
			self.transfer_world_id = None

	def serialize(self, out, is_creation):
		out.write(c_bit(self.activity_flag))
		if self.activity_flag:
			out.write(c_uint(len(self.activity_values)))
			for object_id, values in self.activity_values.items():
				out.write(c_int64(object_id))
				for value in values:
					out.write(c_float(value))
			self.activity_flag = False

	def add_player(self, player):
		self.activity_values[player.object_id] = [0]*10
		self.attr_changed("activity_values")

	def remove_player(self, player):
		del self.activity_values[player.object_id]
		self.attr_changed("activity_values")

	@broadcast
	def activity_start(self):
		pass

	def message_box_respond(self, player, button:c_int=None, id:str=None, user_data:str=None):
		if id == "LobbyReady" and button == 1:
			asyncio.ensure_future(player.char.transfer_to_world((self.transfer_world_id, 0, 0)))

	@single
	def send_activity_summary_leaderboard_data(self, game_id:c_int=None, info_type:c_int=None, leaderboard_data:LDF=None, throttled:bool=None, weekly:bool=None):
		pass

	@broadcast
	def notify_client_zone_object(self, name:str=None, param1:c_int=None, param2:c_int=None, param_obj:GameObject=None, param_str:bytes=None):
		pass
