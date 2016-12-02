import luserver.components.script as script
from luserver.components.inventory import InventoryType
from luserver.components.mission import MissionState, TaskType

MAELSTROM_BRICK = 6194
BRICKS_TO_TAKE = 25
TOKENS_TO_GIVE = 5
INTERACT_MISSION = 863

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		for mission in player.char.missions:
			if mission.id == INTERACT_MISSION:
				player.inventory.remove_item_from_inv(InventoryType.Items, lot=MAELSTROM_BRICK, amount=BRICKS_TO_TAKE)
				player.inventory.add_item_to_inventory(player.char.faction_token_lot(), amount=TOKENS_TO_GIVE)
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.Script and self.object.lot in task.target:
							mission.increment_task(task, player)