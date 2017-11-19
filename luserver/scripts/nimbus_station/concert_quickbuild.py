import luserver.components.script as script
from luserver.components.mission import TaskType

# todo: not fully implemented

class ScriptComponent(script.ScriptComponent):
	def complete_rebuild(self, player):
		player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=283)
