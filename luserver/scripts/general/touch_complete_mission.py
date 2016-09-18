import luserver.components.script as script
from luserver.components.mission import MissionState, TaskType

class ScriptComponent(script.ScriptComponent):
	def on_collision(self, player):
		for mission in player.char.missions:
			if mission.state == MissionState.Active and mission.id == self.script_vars["touch_complete_mission_id"]:
				for task in mission.tasks:
					if task.type == TaskType.Script and self.object.lot in task.target:
						mission.increment_task(task, player)
