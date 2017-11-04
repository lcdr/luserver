import luserver.components.script as script
from luserver.components.inventory import InventoryType

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.inventory.remove_item(InventoryType.Items, lot=self.script_vars["key_lot"])
		player.inventory.add_item(self.script_vars["package_lot"])
