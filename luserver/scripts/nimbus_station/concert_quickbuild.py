import luserver.components.script as script
from luserver.components.mission import TaskType

# todo: not fully implemented

class ScriptComponent(script.ScriptComponent):
	def on_complete_rebuild(self, player):
		player.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=283)
