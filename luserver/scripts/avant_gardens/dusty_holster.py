import luserver.scripts.general.notify_visibility as script
from luserver.game_object import c_int, EB, EI, EP, Player
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.set_missions({1880: ("PlungerGunTargets",)})

	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		super().on_mission_dialogue_o_k(is_complete, mission_state, mission_id, player)
		if mission_id == 1880:
			if mission_state in (MissionState.Available, MissionState.CompletedAvailable):
				player.inventory.add_item(14378)
			elif mission_state in (MissionState.ReadyToComplete, MissionState.CompletedReadyToComplete):
				player.inventory.remove_item(InventoryType.Items, lot=14378)
