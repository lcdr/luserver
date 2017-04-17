import luserver.components.script as script
from luserver.bitstream import c_int
from luserver.game_object import GameObject
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
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int=None, mission_id:c_int=None, player:GameObject=None):
		if mission_state == MissionState.ReadyToComplete:
			if mission_id in package:
				player.inventory.remove_item_from_inv(InventoryType.Items, lot=package[mission_id])
			elif mission_id in flag:
				player.char.set_flag(True, flag[mission_id])
