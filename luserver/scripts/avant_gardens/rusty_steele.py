import luserver.components.script as script
from luserver.game_object import c_int_, GameObject
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

WHEEL = 14555
FLASHLIGHT = 14556

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int_=None, mission_id:c_int_=None, player:GameObject=None):
		if mission_id == 1854 and mission_state == MissionState.ReadyToComplete:
			player.inventory.remove_item(InventoryType.Items, lot=WHEEL, count=4)
			player.inventory.remove_item(InventoryType.Items, lot=FLASHLIGHT, count=3)
