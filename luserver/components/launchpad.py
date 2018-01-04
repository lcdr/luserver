import asyncio
import logging

from pyraknet.bitstream import c_int, c_int64
from ..game_object import GameObject
from ..messages import broadcast
from ..world import server
from .component import Component

log = logging.getLogger(__name__)

class LaunchpadComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.launchpad = self
		self.target_world = server.db.launchpad_component[comp_id][0]
		self.default_world_id = server.db.launchpad_component[comp_id][1]
		self.respawn_point_name = server.db.launchpad_component[comp_id][2]
		if "respawn_point_name" in set_vars:
			self.respawn_point_name = set_vars["respawn_point_name"]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None

		if server.db.config["enabled_worlds"] and self.target_world not in server.db.config["enabled_worlds"]:
			player.char.disp_tooltip("This world is currently disabled.")
			return

		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				self.launch(player, model)
				break
		else:
			player.char.disp_tooltip("You don't have a rocket!")

	def launch(self, player: GameObject, rocket) -> None:
		player.char.traveling_rocket = rocket.module_lots
		self.fire_event_client_side(args="RocketEquipped", obj=rocket, sender=player)

	def fire_event_server_side(self, player, args:str=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=None):
		if args == "ZonePlayer":
			if param2:
				param3 = self.default_world_id
			asyncio.ensure_future(player.char.transfer_to_world((param3, 0, param1), self.respawn_point_name))

	@broadcast
	def fire_event_client_side(self, args:str=None, obj:GameObject=None, param1:c_int64=0, param2:c_int=-1, sender:GameObject=None):
		pass
