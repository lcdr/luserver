import luserver.components.script as script
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=849)
