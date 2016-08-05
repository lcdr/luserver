import luserver.components.script as script
from luserver.components.inventory import InventoryType

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.remove_item_from_inv(InventoryType.Items, lot=self.script_vars["key_lot"])
		player.add_item_to_inventory(self.script_vars["package_lot"])
