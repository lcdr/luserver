import luserver.components.script as script
from luserver.game_object import c_int, E, Player
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

WHEEL = 14555
FLASHLIGHT = 14556

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=E, mission_state:c_int=E, mission_id:c_int=E, player:Player=E):
		if mission_id == 1854 and mission_state == MissionState.ReadyToComplete:
			player.inventory.remove_item(InventoryType.Items, lot=WHEEL, count=4)
			player.inventory.remove_item(InventoryType.Items, lot=FLASHLIGHT, count=3)
