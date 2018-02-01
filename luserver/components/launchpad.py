import asyncio
import logging
from typing import Dict, Optional

from pyraknet.bitstream import WriteStream
from ..game_object import broadcast, c_int, c_int64, E, GameObject, Player
from ..world import server
from .component import Component

log = logging.getLogger(__name__)

class LaunchpadComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Dict[str, object], comp_id: int):
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
			player.char.disp_tooltip("This world is currently disabled.")
			return

		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				self.launch(player, model)
				break
		else:
			player.char.disp_tooltip("You don't have a rocket!")

	def launch(self, player: Player, rocket) -> None:
		player.char.traveling_rocket = rocket.module_lots
		self.fire_event_client_side(args="RocketEquipped", obj=rocket, sender=player)

	def fire_event_server_side(self, player, args:str=E, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=E) -> None:
		if args == "ZonePlayer":
			if param2:
				param3 = self._default_world_id
			asyncio.ensure_future(player.char.transfer_to_world((param3, 0, param1), self._respawn_point_name))

	@broadcast
	def fire_event_client_side(self, args:str=E, obj:GameObject=E, param1:c_int64=0, param2:c_int=-1, sender:GameObject=E) -> None:
		pass
