from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=969)
