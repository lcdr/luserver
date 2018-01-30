import luserver.components.script as script
from luserver.game_object import c_int, E, Player
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=E, mission_state:c_int=E, mission_id:c_int=E, player:Player=E):
		if mission_id == 173 and mission_state == MissionState.ReadyToComplete:
			player.stats.imagination = 6
			player.char.complete_mission(664)
