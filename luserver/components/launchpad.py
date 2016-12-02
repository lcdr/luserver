import asyncio
import logging

from ..bitstream import c_int, c_int64
from .component import Component

log = logging.getLogger(__name__)

class LaunchpadComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.default_world_id = self.object._v_server.db.launchpad_component[comp_id][0]
		self.respawn_point_name = self.object._v_server.db.launchpad_component[comp_id][1]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				self.object._v_server.send_game_message(self.fire_event_client_side, args="RocketEquipped", obj=model.object_id, sender_id=player.object_id, address=player.char.address)
				break
		else:
			log.warning("Player has no rocket!")

	def fire_event_server_side(self, address, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "ZonePlayer":
			player = self.object._v_server.accounts[address].characters.selected()
			if param2:
				param3 = self.default_world_id
			asyncio.ensure_future(player.char.transfer_to_world((param3, 0, param1), self.respawn_point_name))

	def fire_event_client_side(self, address, args:"wstr"=None, obj:c_int64=None, param1:c_int64=0, param2:c_int=-1, sender_id:c_int64=None):
		pass
