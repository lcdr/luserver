import asyncio
from typing import Dict, List

from bitstream import c_float, c_int64, c_uint, WriteStream
from ..game_object import broadcast, c_int, Config, EB, EBY, EI, EL, ES, EO, GameObject, ObjectID, Player, single
from ..world import server
from ..ldf import LDF
from .component import Component

class ScriptedActivityComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.scripted_activity = self
		self._flags["activity_values"] = "activity_flag"
		self.activity_values: Dict[ObjectID, List[float]] = {}
		self.activity_id = comp_id
		if "transfer_world_id" in set_vars:
			self.transfer_world_id = set_vars["transfer_world_id"]
		elif self.activity_id in server.db.activities:
			activity = server.db.activities[self.activity_id]
			self.transfer_world_id = activity[0]
		else:
			self.transfer_world_id = None

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("activity_flag", out):
			out.write(c_uint(len(self.activity_values)))
			for object_id, values in self.activity_values.items():
				out.write(c_int64(object_id))
				for value in values:
					out.write(c_float(value))

	def add_player(self, player: Player) -> None:
		self.activity_values[player.object_id] = [0]*10
		self.attr_changed("activity_values")

	def remove_player(self, player: Player) -> None:
		del self.activity_values[player.object_id]
		self.attr_changed("activity_values")

	@broadcast
	def activity_start(self) -> None:
		pass

	def on_message_box_respond(self, player: Player, button:c_int=EI, id:str=ES, user_data:str=ES) -> None:
		if id == "LobbyReady" and button == 1:
			asyncio.ensure_future(player.char.transfer_to_world((self.transfer_world_id, 0, 0)))

	@single
	def send_activity_summary_leaderboard_data(self, game_id:c_int=EI, info_type:c_int=EI, leaderboard_data:LDF=EL, throttled:bool=EB, weekly:bool=EB) -> None:
		pass

	@broadcast
	def notify_client_zone_object(self, name:str=ES, param1:c_int=EI, param2:c_int=EI, param_obj:GameObject=EO, param_str:bytes=EBY) -> None:
		pass
