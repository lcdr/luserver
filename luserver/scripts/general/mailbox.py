import luserver.components.script as script
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		self._v_server.send_game_message(player.u_i_message_server_to_single_client, str_message_name="pushGameState", args={"state": "Mail"}, address=player.address)

	def fire_event_server_side(self, address, args:"wstr"=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "toggleMail":
			player = self._v_server.game_objects[sender_id]
			self._v_server.send_game_message(player.u_i_message_server_to_single_client, str_message_name="ToggleMail", args={"visible": False}, address=player.address)
