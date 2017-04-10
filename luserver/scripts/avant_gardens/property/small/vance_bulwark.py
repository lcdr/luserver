import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

TRIAL_GEAR = 14359, 14321, 14353, 14315

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 768:
			player = self.object._v_server.game_objects[responder]
			if mission_state == MissionState.Available:
				if not player.char.get_flag(71):
					player.char.play_cinematic(path_name="MissionCam", start_time_advance=0)
			elif mission_state == MissionState.ReadyToComplete:
				for lot in TRIAL_GEAR:
					player.inventory.remove_item_from_inv(InventoryType.Items, lot=lot)
