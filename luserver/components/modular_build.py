from ..bitstream import c_int, c_int64, c_ubyte
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType

class ModularBuildComponent(Component):
	def serialize(self, out, is_creation):
		pass

	def start_building_with_item(self, player, first_time:bool=True, success:bool=None, source_bag:c_int=None, source_id:c_int64=None, source_lot:c_int=None, source_type:c_int=None, target_id:c_int64=None, target_lot:c_int=None, target_pos:Vector3=None, target_type:c_int=None):
		# source is item used for starting, target is module dragged on
		assert first_time
		assert not success
		if source_type == 1:
			source_type = 8

		player.char.start_arranging_with_item(first_time, self.object, player.physics.position, source_bag, source_id, source_lot, source_type, target_id, target_lot, target_pos, target_type)

	def done_arranging_with_item(self, player, new_source_bag:c_int=None, new_source_id:c_int64=None, new_source_lot:c_int=None, new_source_type:c_int=None, new_target_id:c_int64=None, new_target_lot:c_int=None, new_target_type:c_int=None, new_target_pos:Vector3=None, old_item_bag:c_int=None, old_item_id:c_int64=None, old_item_lot:c_int=None, old_item_type:c_int=None):
		for model in player.inventory.temp_models.copy():
			player.inventory.move_item_between_inventory_types(inventory_type_a=InventoryType.TempModels, inventory_type_b=InventoryType.Models, object_id=model.object_id, stack_count=0)

	def modular_build_move_and_equip(self, player, template_id:c_int=None):
		new_item = player.inventory.move_item_between_inventory_types(inventory_type_a=InventoryType.TempModels, inventory_type_b=InventoryType.Models, object_id=0, template_id=template_id)
		player.inventory.equip_inventory(item_to_equip=new_item.object_id)

	def modular_build_finish(self, player, module_lots:(c_ubyte, c_int)=None):
		for model in player.inventory.temp_models.copy():
			if model.lot in module_lots:
				player.inventory.remove_item_from_inv(InventoryType.TempModels, model)

		if self.object.lot == 8044:
			player.inventory.add_item_to_inventory(8092, module_lots=module_lots) # modular car
		else:
			player.inventory.add_item_to_inventory(6416, module_lots=module_lots) # modular rocket
		player.char.finish_arranging_with_item(new_source_bag=0, new_source_id=0, new_source_lot=-1, new_source_type=0, new_target_id=0, new_target_lot=-1, new_target_type=0, new_target_pos=Vector3.zero, old_item_bag=0, old_item_id=0, old_item_lot=-1, old_item_type=0)

	def modular_build_convert_model(self, player, model_id:c_int64=None):
		for model in player.inventory.models:
			if model is not None and model.object_id == model_id:
				for module_lot in model.module_lots:
					player.inventory.add_item_to_inventory(lot=module_lot, inventory_type=InventoryType.TempModels, notify_client=False)
				player.inventory.remove_item_from_inv(InventoryType.Models, model)
				break
