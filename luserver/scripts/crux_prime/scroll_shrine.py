import luserver.components.script as script
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=969)
