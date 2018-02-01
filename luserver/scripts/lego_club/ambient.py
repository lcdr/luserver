from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		self.object.render.play_animation("interact")
