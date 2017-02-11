import logging

from ..bitstream import c_bit, c_int, c_int64, c_uint
from ..messages import single
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType
log = logging.getLogger(__name__)

class VendorComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.vendor = self
		self.items_for_sale = []
		for row in self.object._v_server.db.vendor_component[comp_id]:
			self.items_for_sale.extend(row[0])

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.vendor_open_window(player=player)
		self.vendor_status_update(update_only=False, inv={lot:sort_index for lot, sort_index in self.items_for_sale}, player=player)

	@single
	def vendor_open_window(self):
		pass

	def buy_from_vendor(self, player, confirmed:c_bit=False, count:c_int=1, item:c_int=None):
		for _ in range(count):
			new_item = player.inventory.add_item_to_inventory(lot=item)
			player.char.set_currency(currency=player.char.currency - new_item.base_value, position=Vector3.zero)

	def sell_to_vendor(self, player, count:c_int=1, item_obj_id:c_int64=None):
		for item in player.inventory.items:
			if item is not None and item.object_id == item_obj_id:
				player.char.set_currency(currency=player.char.currency + (item.base_value*count)//10, position=Vector3.zero)
				player.inventory.remove_item_from_inv(InventoryType.Items, object_id=item_obj_id, amount=count)
				break
		else:
			log.warning("Item not found")

	@single
	def vendor_status_update(self, update_only:c_bit=None, inv:(c_uint, c_int, c_int)=None):
		pass
