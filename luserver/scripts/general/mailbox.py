import luserver.components.script as script
from luserver.amf3 import AMF3
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		player.char.u_i_message_server_to_single_client(str_message_name=b"pushGameState", args=AMF3({"state": "Mail"}))

	def fire_event_server_side(self, args:str=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender_id:c_int64=None):
		if args == "toggleMail":
			player = self.object._v_server.game_objects[sender_id]
			player.char.u_i_message_server_to_single_client(str_message_name=b"ToggleMail", args=AMF3({"visible": False}))
