import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.inventory import InventoryType, Stack
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 1728:
			player = self.object._v_server.game_objects[responder]
			if mission_state == MissionState.Available:
				# needed to send the mission mail
				player.char.add_mission(1729)
				player.char.complete_mission(1729)
			elif mission_state == MissionState.ReadyToComplete:
				player.inventory.remove_item_from_inv(InventoryType.Items, lot=14397)
