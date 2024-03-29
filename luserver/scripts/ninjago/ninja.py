import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.mission import MissionState
from luserver.components.inventory import InventoryType

package = {
	1946: 14552,
	1947: 16496,
	1948: 16497,
	1949: 16498}

flag = {
	1796: 2030,
	1952: 2031,
	1959: 2032,
	1962: 2033}

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_state == MissionState.ReadyToComplete:
			if mission_id in package:
				player.inventory.remove_item(InventoryType.Items, lot=package[mission_id])
			elif mission_id in flag:
				player.char.set_flag(True, flag[mission_id])
