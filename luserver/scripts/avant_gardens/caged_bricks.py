from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.world import server
from luserver.components.inventory import InventoryType

FLAG_ID = 74
MAELSTROM_CUBE_LOT = 14553

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.char.set_flag(True, FLAG_ID)
		player.inventory.remove_item(InventoryType.Items, lot=MAELSTROM_CUBE_LOT)
		server.get_objects_in_group("cagedSpider")[0].script.fire_event_client_side(args="toggle", obj=None, sender=player, player=player)
