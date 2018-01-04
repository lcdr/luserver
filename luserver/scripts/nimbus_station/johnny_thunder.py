import luserver.components.script as script
from pyraknet.bitstream import c_int
from luserver.game_object import GameObject
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int=None, mission_id:c_int=None, player:GameObject=None):
		if mission_id == 773 and mission_state == MissionState.Available:
			player.char.add_mission(774)
			player.char.add_mission(775)
			player.char.add_mission(776)
			player.char.add_mission(777)
