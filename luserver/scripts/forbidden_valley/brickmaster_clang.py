import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.mission import MissionState

FREE_NINJAS_MISSION = 705
FREE_NINJAS_MISSIONS = [701, 702, 703, 704]
PANDA_MISSION = 786

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == FREE_NINJAS_MISSION and mission_state == MissionState.Available:
			for mission in FREE_NINJAS_MISSIONS:
				player.char.mission.add_mission(mission)
			player.char.set_flag(True, 68)
		elif mission_id == PANDA_MISSION and mission_state == MissionState.Available:
			player.char.set_flag(True, 81)
