import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 173 and mission_state == MissionState.ReadyToComplete:
			player = self.object._v_server.game_objects[responder]
			player.stats.imagination = 6
			player.char.complete_mission(664)
