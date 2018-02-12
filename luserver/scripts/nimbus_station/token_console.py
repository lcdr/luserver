from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.components.inventory import InventoryType
from luserver.components.mission import TaskType

MAELSTROM_BRICK = 6194
BRICKS_TO_TAKE = 25
TOKENS_TO_GIVE = 5
INTERACT_MISSION = 863

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		if INTERACT_MISSION in player.char.mission.missions:
			player.inventory.remove_item(InventoryType.Items, lot=MAELSTROM_BRICK, count=BRICKS_TO_TAKE)
			player.inventory.add_item(player.char.faction_token_lot(), count=TOKENS_TO_GIVE)

			player.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=INTERACT_MISSION)
