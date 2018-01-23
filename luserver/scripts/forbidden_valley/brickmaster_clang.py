import luserver.components.script as script
from luserver.game_object import c_int_, GameObject
from luserver.components.mission import MissionState

FREE_NINJAS_MISSION = 705
FREE_NINJAS_MISSIONS = [701, 702, 703, 704]
PANDA_MISSION = 786

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int_=None, mission_id:c_int_=None, player:GameObject=None):
		if mission_id == FREE_NINJAS_MISSION and mission_state == MissionState.Available:
			for mission in FREE_NINJAS_MISSIONS:
				player.char.add_mission(mission)
			player.char.set_flag(True, 68)
		elif mission_id == PANDA_MISSION and mission_state == MissionState.Available:
			player.char.set_flag(True, 81)
