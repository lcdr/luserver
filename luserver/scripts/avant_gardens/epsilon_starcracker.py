import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 1851 and mission_state == MissionState.ReadyToComplete:
			player = self.object._v_server.game_objects[responder]
			player.char.start_celebration_effect(animation="", duration=0, icon_id=0, main_text="", mixer_program="", music_cue="", path_node_name="", sound_guid="", sub_text="", celebration_id=22)