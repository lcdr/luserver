import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

POSTCARD = 14549
TRIAL_GEAR = 14359, 14321, 14353, 14315

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		if mission_id == 313 and mission_state == MissionState.ReadyToComplete:
			player = self.object._v_server.game_objects[responder]
			player.inventory.remove_item_from_inv(InventoryType.Items, lot=POSTCARD, amount=5)
			for lot in TRIAL_GEAR:
				player.inventory.remove_item_from_inv(InventoryType.Items, lot=lot)
