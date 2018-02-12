from typing import cast

import luserver.components.script as script
from luserver.game_object import c_int, EB, EI, EO, GameObject, ScriptObject
from luserver.world import server
from luserver.components.mission import MissionState

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.missions = {}

	def set_missions(self, missions):
		self.missions = missions

	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:GameObject=EO):
		if mission_id in self.missions:
			if mission_state in (MissionState.Available, MissionState.CompletedAvailable):
				visible = 1
			elif mission_state in (MissionState.ReadyToComplete, MissionState.CompletedReadyToComplete):
				visible = 0
			else:
				return
			spawners = []
			for spawner_name in self.missions[mission_id]:
				spawners.append(server.spawners[spawner_name])

			for obj in server.game_objects.values():
				if obj.spawner_object in spawners:
					cast(ScriptObject, obj).script.notify_client_object(name="SetVisibility", param1=visible, param2=0, param_obj=None, param_str=b"")
