from ..bitstream import c_bit, c_int, c_int64, c_ubyte
from ..math.vector import Vector3
from .inventory import InventoryType

class ModularBuildComponent:
	def __init__(self, comp_id):
		pass

	def serialize(self, out, is_creation):
		pass

	def start_building_with_item(self, address, first_time:c_bit=True, success:c_bit=None, source_bag:c_int=None, source_id:c_int64=None, source_lot:c_int=None, source_type:c_int=None, target_id:c_int64=None, target_lot:c_int=None, target_pos:Vector3=None, target_type:c_int=None):
		# source is item used for starting, target is module dragged on
		assert first_time
		assert not success
		if source_type == 1:
			source_type = 8

		player = self._v_server.accounts[address].characters.selected()
		self._v_server.send_game_message(player.start_arranging_with_item, first_time, self.object_id, player.position, source_bag, source_id, source_lot, source_type, target_id, target_lot, target_pos, target_type, address=address)

	def modular_build_finish(self, address, module_lots:(c_ubyte, c_int)=None):
		player = self._v_server.accounts[address].characters.selected()
		for model in player.temp_models.copy():
			if model.lot in module_lots:
				player.remove_item_from_inv(InventoryType.TempModels, model)

		if self.lot == 8044:
			player.add_item_to_inventory(8092, module_lots=module_lots) # modular car
		else:
			player.add_item_to_inventory(6416, module_lots=module_lots) # modular rocket
		self._v_server.send_game_message(player.finish_arranging_with_item, new_source_bag=0, new_source_id=0, new_source_lot=-1, new_source_type=0, new_target_id=0, new_target_lot=-1, new_target_type=0, new_target_pos=Vector3.zero, old_item_bag=0, old_item_id=0, old_item_lot=-1, old_item_type=0, address=address)

	def modular_build_convert_model(self, address, model_id:c_int64=None):
		player = self._v_server.accounts[address].characters.selected()
		for model in player.models:
			if model is not None and model.object_id == model_id:
				for module_lot in model.module_lots:
					player.add_item_to_inventory(lot=module_lot, inventory_type=InventoryType.TempModels, notify_client=False)
				player.remove_item_from_inv(InventoryType.Models, model)
				break
