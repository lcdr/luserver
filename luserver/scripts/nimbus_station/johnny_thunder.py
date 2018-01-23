import luserver.components.script as script
from luserver.game_object import c_int_, GameObject
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int_=None, mission_id:c_int_=None, player:GameObject=None):
		if mission_id == 773 and mission_state == MissionState.Available:
			player.char.add_mission(774)
			player.char.add_mission(775)
			player.char.add_mission(776)
			player.char.add_mission(777)
