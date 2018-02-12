import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 773 and mission_state == MissionState.Available:
			player.char.mission.add_mission(774)
			player.char.mission.add_mission(775)
			player.char.mission.add_mission(776)
			player.char.mission.add_mission(777)
