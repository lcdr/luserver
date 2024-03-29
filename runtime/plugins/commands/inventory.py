from luserver.auth import GMLevel
from luserver.components.inventory import InventoryType
from luserver.interfaces.plugin import ChatCommand, instance_player

class AddItem(ChatCommand):
	def __init__(self):
		super().__init__("additem")
		self.command.set_defaults(perm=GMLevel.Mod)
		self.command.add_argument("lot", type=int)
		self.command.add_argument("--count", type=int, default=1)
		self.command.add_argument("--player", type=instance_player)

	def run(self, args, sender):
		if args.player is None:
			args.player = sender
		args.player.inventory.add_item(args.lot, args.count)

class ExtendInventory(ChatCommand):
	def __init__(self):
		super().__init__("extendinv")
		self.command.add_argument("count", type=int)

	def run(self, args, sender):
		# currently just items, add models functionality when necessary
		sender.inventory.set_inventory_size(inventory_type=InventoryType.Items, size=len(sender.inventory.items)+args.count)

class FactionTokens(ChatCommand):
	def __init__(self):
		super().__init__("factiontokens")

	def run(self, args, sender):
		sender.inventory.add_item(8318, 100)
		sender.inventory.add_item(8319, 100)
		sender.inventory.add_item(8320, 100)
		sender.inventory.add_item(8321, 100)
