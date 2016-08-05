import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionNPCComponent, MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, address, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		MissionNPCComponent.mission_dialogue_o_k(self, address, is_complete, mission_state, mission_id, responder)

		if mission_id == 173 and mission_state == MissionState.ReadyToComplete:
			player = self._v_server.game_objects[responder]
			player.imagination = 6
			for mission in player.missions:
				if mission.id == 664:
					mission.complete(self._v_server, player)
					break
