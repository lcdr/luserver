from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.components.inventory import InventoryType

AURA_BLOSSOM = 12317
TEA = 12109

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		player.inventory.remove_item(InventoryType.Items, lot=AURA_BLOSSOM, count=10)
		player.inventory.add_item(TEA)
