import asyncio
from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		asyncio.ensure_future(player.char.transfer_to_world((self.script_vars["transfer_world_id"], 0, 0), respawn_point_name=""))
