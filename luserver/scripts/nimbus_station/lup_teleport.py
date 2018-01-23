import luserver.scripts.general.teleport_to_ns_or_nt as script
from luserver.game_object import c_int_
from luserver.world import server
from luserver.components.char import TerminateType

# todo: not completely implemented
# todo: implement visited worlds so the NS/NT choice UI can work

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		# todo: check if player has been to NT, if yes then display choice UI
		if server.world_id[0] == 1600:
			text = "UI_TRAVEL_TO_NS"
		else:
			text = "UI_TRAVEL_TO_LUP_STATION"
		player.char.disp_message_box(id="TransferBox", text=text, callback=self.object)

	def message_box_respond(self, player, button:c_int_=None, id:str=None, user_data:str=None):
		if id == "TransferBox":
			if button == 1:
				# todo: display zone summary (callback not working right now for some reason)
				#player.char.display_zone_summary(sender=self.object)
				if server.world_id[0] == 1600:
					dest = 1200
					spawnpoint = "NS_LW"
				else:
					dest = 1600
					spawnpoint = ""
				self.transfer(player, (dest, 0, 0), spawnpoint)
			else:
				player.char.terminate_interaction(terminator=self.object, type=TerminateType.FromInteraction)
