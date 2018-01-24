import luserver.scripts.general.console_teleport as script
from luserver.game_object import c_int, E
from luserver.components.char import TerminateType

# todo: implement visited worlds so the NS/NT choice UI can work

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		# todo: check if player has been to NT, if yes then display choice UI
		player.char.disp_message_box(id="TransferBox", text="UI_TRAVEL_TO_LUP_STATION", callback=self.object)

	def message_box_respond(self, player, button:c_int=E, id:str=E, user_data:str=E):
		if id == "TransferBox":
			if button == 1:
				# todo: display zone summary (callback not working right now for some reason)
				#player.char.display_zone_summary(sender=self.object)
				self.transfer(player, (1200, 0, 0), "NS_LEGO_Club")
			else:
				player.char.terminate_interaction(terminator=self.object, type=TerminateType.FromInteraction)
