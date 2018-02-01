from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.world import server
from luserver.components.inventory import InventoryType

RED_IMAGINITE = 3040

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		if player.inventory.has_item(InventoryType.Items, RED_IMAGINITE):
			rewards = server.db.activity_rewards[self.object.scripted_activity.activity_id]
			self.object.physics.drop_rewards(*rewards, player)
			player.inventory.remove_item(InventoryType.Items, lot=RED_IMAGINITE)
