import luserver.components.script as script
from luserver.bitstream import c_int
from luserver.game_object import GameObject
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

TRIAL_GEAR = 14359, 14321, 14353, 14315

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int=None, mission_id:c_int=None, player:GameObject=None):
		if mission_id == 320:
			if mission_state == MissionState.Available:
				self.object._v_server.world_control_object.script.notify_client_object(name="GuardChat", param1=0, param2=0, param_str=b"", param_obj=self.object)
				self.object.call_later(5, self.die_vacuum)
		elif mission_id == 768:
			if mission_state == MissionState.Available:
				if not player.char.get_flag(71):
					player.char.play_cinematic(path_name="MissionCam", start_time_advance=0)
			elif mission_state == MissionState.ReadyToComplete:
				for lot in TRIAL_GEAR:
					player.inventory.remove_item_from_inv(InventoryType.Items, lot=lot)

	def die_vacuum(self):
		self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=self.object.object_id, loot_owner_id=0)
		self.object._v_server.spawners["PropertyGuard"].spawner.deactivate()
