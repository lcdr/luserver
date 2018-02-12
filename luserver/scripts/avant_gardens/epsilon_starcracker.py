import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 1851 and mission_state == MissionState.ReadyToComplete:
			player.char.start_celebration_effect(animation="", duration=0, icon_id=0, main_text="", mixer_program=b"", music_cue=b"", path_node_name=b"", sound_guid=b"", sub_text="", celebration_id=22)
