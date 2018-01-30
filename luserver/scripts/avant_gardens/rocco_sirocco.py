import luserver.components.script as script
from luserver.game_object import c_int, E, GameObject, Player, single
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, is_complete:bool=E, mission_state:c_int=E, mission_id:c_int=E, player:Player=E):
		if mission_id == 1728:
			if mission_state == MissionState.Available:
				# needed to send the mission mail
				player.char.add_mission(1729)
				player.char.complete_mission(1729)
			elif mission_state == MissionState.ReadyToComplete:
				player.inventory.remove_item(InventoryType.Items, lot=14397)
				self.notify_client_object(name="switch", param1=0, param2=0, param_str=b"", param_obj=None, player=player)

	# manually changed from broadcast to single because the client script abuses this message
	# see also caged_spider
	@single
	def notify_client_object(self, name:str=E, param1:c_int=E, param2:c_int=E, param_obj:GameObject=E, param_str:bytes=E):
		pass
