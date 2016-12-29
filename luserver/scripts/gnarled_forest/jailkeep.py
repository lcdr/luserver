import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionState

FEED_NINJAS_MISSION = 385
FEED_NINJAS_MISSIONS = [386, 387, 388, 390]

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == FEED_NINJAS_MISSION and mission_state == MissionState.Available:
			player = self.object._v_server.game_objects[responder]
			for mission in FEED_NINJAS_MISSIONS:
				player.char.add_mission(mission)
