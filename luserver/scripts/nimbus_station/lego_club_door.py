from typing import Optional

import luserver.scripts.general.teleport_to_ns_or_nt as script
from luserver.amf3 import AMF3
from luserver.game_object import c_int, EI, ES, Player
from luserver.world import server
from luserver.components.char import TerminateType

# todo: not completely implemented
# todo: implement visited worlds so the NS/NT choice UI can work

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		if server.world_id[0] == 1700:
			# todo: check if player has been to NT, if yes then display choice UI
			player.char.disp_message_box(id="TransferBox", text="UI_TRAVEL_TO_NS", callback=self.object)
		else:
			player.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "Lobby", "context": {"user": str(player.object_id), "callbackObj": str(self.object.object_id), "HelpVisible": "show", "type": "Lego_Club_Valid"}}))

	def message_box_respond(self, player, button:c_int=EI, id:str=ES, user_data:str=ES):
		if id == "PlayButton":
			self.transfer(player, (1700, 0, 0), "")
		elif id == "TransferBox":
			if button == 1:
				# todo: display zone summary (callback not working right now for some reason)
				#player.char.display_zone_summary(sender=self.object)
				self.transfer(player, (1200, 0, 0), "NS_LEGO_Club")
			else:
				player.char.terminate_interaction(terminator=self.object, type=TerminateType.FromInteraction)
