import luserver.components.script as script
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_skill_event(self, caster, event_name):
		if event_name == "spinjitzu":
			caster.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=966)
