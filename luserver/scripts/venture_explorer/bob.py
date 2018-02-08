import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 173 and mission_state == MissionState.ReadyToComplete:
			player.stats.imagination = 6
			player.char.complete_mission(664)
