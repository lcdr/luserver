import luserver.scripts.general.notify_visibility as script
from pyraknet.bitstream import c_int
from luserver.game_object import GameObject
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.set_missions({1880: ("PlungerGunTargets",)})

	def mission_dialogue_o_k(self, is_complete:bool=None, mission_state:c_int=None, mission_id:c_int=None, player:GameObject=None):
		super().mission_dialogue_o_k(is_complete, mission_state, mission_id, player)
		if mission_id == 1880:
			if mission_state in (MissionState.Available, MissionState.CompletedAvailable):
				player.inventory.add_item(14378)
			elif mission_state in (MissionState.ReadyToComplete, MissionState.CompletedReadyToComplete):
				player.inventory.remove_item(InventoryType.Items, lot=14378)
