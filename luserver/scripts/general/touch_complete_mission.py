import luserver.components.script as script
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=self.script_vars["touch_complete_mission_id"])
