import logging
from typing import Dict, Optional

from pyraknet.bitstream import c_bit, c_uint, WriteStream
from ..game_object import c_int, c_int64, E, GameObject, Mapping, Player, single
from ..world import server
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType
log = logging.getLogger(__name__)

class VendorComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Dict[str, object], comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.vendor = self
		self.items_for_sale = []
		for row in server.db.vendor_component[comp_id]:
			self.items_for_sale.extend(server.db.loot_table[row[0]])

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		self.vendor_open_window(player=player)
		self.vendor_status_update(update_only=False, inv={lot:sort_index for lot, _, sort_index in self.items_for_sale}, player=player)

	@single
	def vendor_open_window(self) -> None:
		pass

	def buy_from_vendor(self, player, confirmed:bool=False, count:c_int=1, item:c_int=E) -> None:
		new_item = player.inventory.add_item(item, count)
		player.char.set_currency(currency=player.char.currency - new_item.base_value*count, position=Vector3.zero)

	def sell_to_vendor(self, player, count:c_int=1, item_obj_id:c_int64=E) -> None:
		found = False
		for inv_type in (InventoryType.Items, InventoryType.Models, InventoryType.Bricks):
			inv = player.inventory.inventory_type_to_inventory(inv_type)
			for item in inv:
				if item is not None and item.object_id == item_obj_id:
					player.char.set_currency(currency=player.char.currency + (item.base_value*count)//10, position=Vector3.zero)
					player.inventory.remove_item(inv_type, object_id=item_obj_id, count=count)
					found = True
					break
		if not found:
			log.warning("Item not found")

	@single
	def vendor_status_update(self, update_only:bool=E, inv:Mapping[c_uint, c_int, c_int]=E) -> None:
		pass
