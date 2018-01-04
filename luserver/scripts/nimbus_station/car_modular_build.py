import luserver.components.script as script
from luserver.components.mission import MissionState, TaskType
from pyraknet.bitstream import c_int, c_ubyte
from luserver.messages import Sequence

CAR_MISSION = 623

class ScriptComponent(script.ScriptComponent):
	def modular_build_finish(self, player, module_lots:Sequence[c_ubyte, c_int]=None):
		if CAR_MISSION in player.char.missions and player.char.missions[CAR_MISSION].state == MissionState.Active:
			player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=CAR_MISSION)
