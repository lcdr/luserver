from typing import Optional

import luserver.components.script as script
from luserver.amf3 import AMF3
from luserver.game_object import c_int, EP, ES, Player

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		player.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "bank"}))

	def fire_event_server_side(self, args:str=ES, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:Player=EP):
		if args == "ToggleBank":
			sender.char.u_i_message_server_to_single_client(message_name=b"ToggleBank", args=AMF3({"visible": False}))
