import luserver.components.script as script
from luserver.components.mission import MissionState, TaskType
from luserver.bitstream import c_int, c_ubyte

MARDOLF_ROCKET_MISSION = 809
ROCKET_MISSION_PARTS = 9516, 9517, 9518

class ScriptComponent(script.ScriptComponent):
	def modular_build_finish(self, player, module_lots:(c_ubyte, c_int)=None):
		print("jio"*4, module_lots)
		if MARDOLF_ROCKET_MISSION in player.char.missions and player.char.missions[MARDOLF_ROCKET_MISSION].state == MissionState.Active:
			for lot in module_lots:
				if lot in ROCKET_MISSION_PARTS:
					player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=MARDOLF_ROCKET_MISSION)
