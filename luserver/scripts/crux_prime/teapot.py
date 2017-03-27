import luserver.components.script as script
from luserver.components.inventory import InventoryType

AURA_BLOSSOM = 12317
TEA = 12109

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		player.inventory.remove_item_from_inv(InventoryType.Items, lot=AURA_BLOSSOM, amount=10)
		player.inventory.add_item_to_inventory(TEA)
