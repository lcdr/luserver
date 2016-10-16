import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionState

FREE_NINJAS_MISSION = 705
FREE_NINJAS_MISSIONS = [701, 702, 703, 704]

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, address, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		player = self.object._v_server.game_objects[responder]
		if mission_id == FREE_NINJAS_MISSION and mission_state == MissionState.Available:
			for mission in FREE_NINJAS_MISSIONS:
				player.char.add_mission(mission)
			player.set_flag(None, True, 68)
		elif mission_ID == PANDA_MISSION and mission_state == MissionState.Available:
			self.object._v_server.send_game_message(player.set_flag, True, 81, address=player.char.address)