import luserver.components.script as script
from luserver.game_object import c_int, EB, EBY, EI, EO, EP, ES, GameObject, Player, single
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP):
		if mission_id == 1728:
			if mission_state == MissionState.Available:
				# needed to send the mission mail
				player.char.mission.add_mission(1729)
				player.char.mission.complete_mission(1729)
			elif mission_state == MissionState.ReadyToComplete:
				player.inventory.remove_item(InventoryType.Items, lot=14397)
				self.notify_client_object(name="switch", param1=0, param2=0, param_str=b"", param_obj=None, player=player)

	# manually changed from broadcast to single because the client script abuses this message
	# see also caged_spider
	@single
	def notify_client_object(self, name:str=ES, param1:c_int=EI, param2:c_int=EI, param_obj:GameObject=EO, param_str:bytes=EBY):
		pass
