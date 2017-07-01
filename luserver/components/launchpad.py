import asyncio
import logging

from ..bitstream import c_int, c_int64
from ..game_object import GameObject
from ..ldf import LDF
from ..messages import broadcast
from ..world import server
from .component import Component

log = logging.getLogger(__name__)

class LaunchpadComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.default_world_id = server.db.launchpad_component[comp_id][0]
		self.respawn_point_name = server.db.launchpad_component[comp_id][1]
		if "respawn_point_name" in set_vars:
			self.respawn_point_name = set_vars["respawn_point_name"]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				player.char.traveling_rocket = model.module_lots
				self.fire_event_client_side(args="RocketEquipped", obj=model, sender=player)
				break
		else:
			player.char.display_tooltip(show=True, time=1000, id="", localize_params=LDF(), str_image_name="", str_text="You don't have a rocket!")

	def fire_event_server_side(self, player, args:str=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "ZonePlayer":
			if param2:
				param3 = self.default_world_id
			asyncio.ensure_future(player.char.transfer_to_world((param3, 0, param1), self.respawn_point_name))

	@broadcast
	def fire_event_client_side(self, args:str=None, obj:GameObject=None, param1:c_int64=0, param2:c_int=-1, sender:GameObject=None):
		pass
