from ..components.inventory import InventoryType
from .command import ChatCommand

class AddItem(ChatCommand):
	def __init__(self):
		super().__init__("additem")
		self.command.add_argument("lot", type=int)
		self.command.add_argument("--amount", type=int, default=1)

	def run(self, args, sender):
		sender.inventory.add_item_to_inventory(args.lot, args.amount)

class ExtendInventory(ChatCommand):
	def __init__(self):
		super().__init__("extendinv")
		self.command.add_argument("amount", type=int)

	def run(self, args, sender):
		# currently just items, add models functionality when necessary
		sender.inventory.set_inventory_size(inventory_type=InventoryType.Items, size=len(sender.inventory.items)+args.amount)

class FactionTokens(ChatCommand):
	def __init__(self):
		super().__init__("factiontokens")

	def run(self, args, sender):
		sender.inventory.add_item_to_inventory(8318, 100)
		sender.inventory.add_item_to_inventory(8319, 100)
		sender.inventory.add_item_to_inventory(8320, 100)
		sender.inventory.add_item_to_inventory(8321, 100)
