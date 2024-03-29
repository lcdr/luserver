import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

POSTCARD = 14549
TRIAL_GEAR = 14359, 14321, 14353, 14315

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 313 and mission_state == MissionState.ReadyToComplete:
			player.inventory.remove_item(InventoryType.Items, lot=POSTCARD, count=5)
			for lot in TRIAL_GEAR:
				player.inventory.remove_item(InventoryType.Items, lot=lot)
