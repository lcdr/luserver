import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 1849:
			if mission_state == MissionState.Available:
				visible = 1
			elif mission_state == MissionState.ReadyToComplete:
				visible = 0
				player = self.object._v_server.game_objects[responder]
				player.inventory.remove_item_from_inv(InventoryType.Items, lot=14592)
			else:
				return
			for obj in self.object._v_server.game_objects.values():
				if obj.lot == 14718:
					obj.script.notify_client_object(name="SetVisibility", param1=visible, param2=0, param_obj=0, param_str="")
