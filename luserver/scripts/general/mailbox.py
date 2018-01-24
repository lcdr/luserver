import luserver.components.script as script
from luserver.amf3 import AMF3
from luserver.game_object import c_int, E, GameObject

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		player.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "Mail"}))

	def fire_event_server_side(self, args:str=E, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=E):
		if args == "toggleMail":
			sender.char.u_i_message_server_to_single_client(message_name=b"ToggleMail", args=AMF3({"visible": False}))
