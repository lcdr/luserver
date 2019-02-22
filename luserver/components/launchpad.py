import asyncio
import logging
from typing import Optional

from bitstream import WriteStream
from ..game_object import broadcast, c_int, c_int64, Config, EO, ES, GameObject, Player
from ..world import server
from .component import Component
from .inventory import Stack

log = logging.getLogger(__name__)

class LaunchpadComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.launchpad = self
		self._target_world = server.db.launchpad_component[comp_id][0]
		self._default_world_id = server.db.launchpad_component[comp_id][1]
		self._respawn_point_name = server.db.launchpad_component[comp_id][2]
		if "respawn_point_name" in set_vars:
			self._respawn_point_name = set_vars["respawn_point_name"]

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None

		if server.db.config["enabled_worlds"] and self._target_world not in server.db.config["enabled_worlds"]:
			player.char.ui.disp_tooltip("This world is currently disabled.")
			return

		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				self.launch(player, model)
				break
		else:
			player.char.ui.disp_tooltip("You don't have a rocket!")

	def launch(self, player: Player, rocket: Stack) -> None:
		player.char.traveling_rocket = rocket.module_lots
		self.fire_event_client_side(args="RocketEquipped", obj=rocket, sender=player)

	def on_fire_event_server_side(self, player: Player, args:str=ES, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=EO) -> None:
		if args == "ZonePlayer":
			if param2:
				param3 = self._default_world_id
			asyncio.ensure_future(player.char.transfer_to_world((param3, 0, param1), self._respawn_point_name))

	@broadcast
	def fire_event_client_side(self, args:str=ES, obj:GameObject=EO, param1:c_int64=0, param2:c_int=-1, sender:GameObject=EO) -> None:
		pass
