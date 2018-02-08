import luserver.components.script as script
from luserver.game_object import c_int, E, Player
from luserver.world import server
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

TRIAL_GEAR = 14359, 14321, 14353, 14315

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 320:
			if mission_state == MissionState.Available:
				server.world_control_object.script.notify_client_object(name="GuardChat", param1=0, param2=0, param_str=b"", param_obj=self.object)
				self.object.call_later(5, self.die_vacuum)
		elif mission_id == 768:
			if mission_state == MissionState.Available:
				if not player.char.get_flag(71):
					player.char.play_cinematic(path_name="MissionCam", start_time_advance=0)
			elif mission_state == MissionState.ReadyToComplete:
				for lot in TRIAL_GEAR:
					player.inventory.remove_item(InventoryType.Items, lot=lot)

	def die_vacuum(self):
		self.object.destructible.simply_die(killer=self.object)
		server.spawners["PropertyGuard"].spawner.deactivate()
