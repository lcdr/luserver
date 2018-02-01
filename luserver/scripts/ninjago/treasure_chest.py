from typing import Optional
import luserver.components.script as script
from luserver.game_object import Player
from luserver.components.inventory import InventoryType

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.inventory.remove_item(InventoryType.Items, lot=self.script_vars["key_lot"])
		player.inventory.add_item(self.script_vars["package_lot"])
