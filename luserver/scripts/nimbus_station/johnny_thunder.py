import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 773 and mission_state == MissionState.Available:
			player = self.object._v_server.game_objects[responder]
			player.char.add_mission(774)
			player.char.add_mission(775)
			player.char.add_mission(776)
			player.char.add_mission(777)
