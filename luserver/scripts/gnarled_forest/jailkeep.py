import luserver.components.script as script
from luserver.game_object import c_int_, GameObject
from luserver.components.mission import MissionState

FEED_NINJAS_MISSION = 385
FEED_NINJAS_MISSIONS = [386, 387, 388, 390]

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int_=None, mission_id:c_int_=None, player:GameObject=None):
		if mission_id == FEED_NINJAS_MISSION and mission_state == MissionState.Available:
			for mission in FEED_NINJAS_MISSIONS:
				player.char.add_mission(mission)
