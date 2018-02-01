from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.char.set_flag(True, flag_id=server.world_id[0]+self.script_vars["flag_id"])
		self.object.script.fire_event_client_side(args="achieve", obj=None, sender=None)
