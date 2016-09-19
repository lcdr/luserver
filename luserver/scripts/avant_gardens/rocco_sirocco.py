import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.inventory import Stack
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, address, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 1728 and mission_state == MissionState.Available:
			player = self.object._v_server.game_objects[responder]
			item = Stack(self.object._v_server.db, self.object._v_server.new_object_id(), 14397)
			self.object._v_server.mail.send_mail("Workaround", "Mission item", "Workaround: this should be implemented with a generic mission mail system but for this mission there is no matching capture. To do: implement generic system", player, item)
