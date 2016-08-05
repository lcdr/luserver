import asyncio
import logging

from ..bitstream import c_int, c_int64

log = logging.getLogger(__name__)

class LaunchpadComponent:
	def __init__(self, comp_id):
		self.default_world_id = self._v_server.db.launchpad_component[comp_id][0]
		self.respawn_point_name = self._v_server.db.launchpad_component[comp_id][1]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		for model in player.models:
			if model is not None and model.lot == 6416:
				self._v_server.send_game_message(self.fire_event_client_side, args="RocketEquipped", obj=model.object_id, sender_id=player.object_id, address=player.address)
				break
		else:
			log.warning("Player has no rocket!")

	def fire_event_server_side(self, address, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "ZonePlayer":
			player = self._v_server.accounts[address].characters.selected()
			if param2:
				param3 = self.default_world_id
			asyncio.ensure_future(player.transfer_to_world((param3, 0, param1), self.respawn_point_name))
