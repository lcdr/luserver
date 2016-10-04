import luserver.components.script as script
from luserver.components.mission import MissionState, TaskType

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		for mission in player.char.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.Discover and task.target == self.script_vars["poi"]:
						mission.increment_task(task, player)
