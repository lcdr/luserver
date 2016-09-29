class InventoryType:
	Items = 0
	Bricks = 2
	# temp items = 4?
	Models = 5
	TempModels = 6
	# Properties = 8 ?
	# VendorSellSpace = 11
	MissionObjects = 12

class ItemType:
	Brick = 1
	Hat = 2
	Hair = 3
	Neck = 4
	LeftHand = 5
	RightHand = 6
	Pants = 7
	SomeOtherKindOfMissionObject = 13
	Consumable = 14
	Chest = 15
	MissionObject = 18
	Package = 20
	Model = 21
	Vehicle = 22
	Mount = 24

class LootType:
	Mission = 2
	Achievement = 5
	# loot drop = 11 ?

import logging

from persistent import Persistent
from persistent.list import PersistentList

from ..bitstream import c_bit, c_int, c_int64, c_uint
from ..math.vector import Vector3
from .component import Component
from .mission import MissionState, TaskType

log = logging.getLogger(__name__)

class Stack(Persistent):
	def __init__(self, db, object_id, lot):
		self.object_id = object_id
		self.lot = lot
		self.amount = 1
		self.equipped = False

		for component_type, component_id in db.components_registry[self.lot]:
			if component_type == 11: # ItemComponent, make an enum for this somewhen
				self.base_value = db.item_component[component_id][0]
				self.item_type = db.item_component[component_id][1]
				break
		else:
			log.error("ItemComponent for LOT %i not found!", self.lot)

	def __repr__(self):
		return "%ix %i" % (self.amount, self.lot)

class ItemComponent(Component):
	def serialize(self, out, is_creation):
		out.write(c_bit(False))

class InventoryComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.inventory = self
		self.equipped_items_flag = False
		self.items = PersistentList([None]*20)
		self.bricks = PersistentList()
		self.models = PersistentList([None]*200)
		self.temp_models = PersistentList()
		self.mission_objects = PersistentList()

		if comp_id in self.object._v_server.db.inventory_component:
			for item_lot, equip in self.object._v_server.db.inventory_component[comp_id]:
				item = self.add_item_to_inventory(item_lot, persistent=False, notify_client=False)
				if equip:
					self.equip_inventory(None, item_to_equip=item.object_id)

	def serialize(self, out, is_creation):
		out.write(c_bit(self.equipped_items_flag or is_creation))
		if self.equipped_items_flag or is_creation:
			equipped_items = [i for i in self.items if i is not None and i.equipped]
			equipped_models = [i for i in self.models if i is not None and i.equipped]
			equipped_items.extend(equipped_models)
			out.write(c_uint(len(equipped_items)))
			for item in equipped_items:
				out.write(c_int64(item.object_id))
				out.write(c_int(item.lot))
				out.write(c_bit(False))
				out.write(c_bit(False))
				out.write(c_bit(False))
				out.write(c_bit(item in equipped_models))
				if item in equipped_models:
					out.write(c_uint(5))
				out.write(c_bit(False))
				out.write(c_bit(item not in equipped_models))
			self.equipped_items_flag = False
		out.write(c_bit(False))

	def inventory_type_to_inventory(self, inventory_type):
		if inventory_type == InventoryType.Items:
			return self.items
		if inventory_type == InventoryType.Bricks:
			return self.bricks
		if inventory_type == InventoryType.Models:
			return self.models
		if inventory_type == InventoryType.TempModels:
			return self.temp_models
		if inventory_type == InventoryType.MissionObjects:
			return self.mission_objects
		raise NotImplementedError(inventory_type)

	def move_item_in_inventory(self, address, dest_inventory_type:c_int=0, object_id:c_int64=None, inventory_type:c_int=None, response_code:c_int=None, slot:c_int=None):
		assert dest_inventory_type == 0
		assert object_id != 0
		assert response_code == 0
		inventory = self.inventory_type_to_inventory(inventory_type)

		for item in inventory:
			if item is not None and item.object_id == object_id:
				inventory[inventory.index(item)] = inventory[slot]
				inventory[slot] = item
				break

	def add_item_to_inventory(self, lot, amount=1, module_lots=None, inventory_type=None, source_type=0, show_flying_loot=True, persistent=True, notify_client=True):
		for component_type, component_id in self.object._v_server.db.components_registry[lot]:
			if component_type == 11: # ItemComponent, make an enum for this somewhen
				item_type, stack_size = self.object._v_server.db.item_component[component_id][1:]
				break
		else:
			raise ValueError("lot", lot)
			# no item component found

		if inventory_type is None:
			if item_type == ItemType.Brick:
				inventory_type = InventoryType.Bricks
			elif item_type in (ItemType.Hat, ItemType.Hair, ItemType.Neck, ItemType.LeftHand, ItemType.RightHand, ItemType.Pants, ItemType.SomeOtherKindOfMissionObject, ItemType.Consumable, ItemType.Chest, ItemType.Package, ItemType.Mount):
				inventory_type = InventoryType.Items
			elif item_type == ItemType.MissionObject:
				inventory_type = InventoryType.MissionObjects
			elif item_type in (ItemType.Model, ItemType.Vehicle):
				inventory_type = InventoryType.Models
			else:
				raise NotImplementedError(lot, item_type)
		inventory = self.inventory_type_to_inventory(inventory_type)

		for _ in range(amount):
			new_stack = stack_size == 1
			if not new_stack:
				for stack in inventory:
					if stack is not None and stack.lot == lot and (stack_size == 0 or stack.amount < stack_size):
						stack.amount += 1
						index = inventory.index(stack)
						break
				else:
					new_stack = True

			if new_stack:
				if persistent:
					object_id = self.object._v_server.new_object_id()
				else:
					object_id = self.object._v_server.new_spawned_id()
				stack = Stack(self.object._v_server.db, object_id, lot)

				if inventory_type in (InventoryType.Bricks, InventoryType.TempModels, InventoryType.MissionObjects):
					inventory.append(stack)
					index = len(inventory)-1
				else:
					for index, item in enumerate(inventory):
						if item is None:
							inventory[index] = stack
							break
					else:
						log.error("no space left")
						self.object._v_server.mail.send_mail("%[MAIL_SYSTEM_NOTIFICATION]", "%[MAIL_ACHIEVEMENT_OVERFLOW_HEADER]", "%[MAIL_ACHIEVEMENT_OVERFLOW_BODY]", self.object, stack)
						return # should probably throw an exception?

			if module_lots:
				stack.module_lots = module_lots

			if notify_client:
				extra_info = {}
				if hasattr(stack, "module_lots"):
					extra_info["assemblyPartLOTs"] = str, [(c_int, i) for i in stack.module_lots]

				self.object._v_server.send_game_message(self.add_item_to_inventory_client_sync, bound=True, bound_on_equip=True, bound_on_pickup=True, loot_type_source=source_type, extra_info=extra_info, object_template=stack.lot, inv_type=inventory_type, amount=1, new_obj_id=stack.object_id, flying_loot_pos=Vector3.zero, show_flying_loot=show_flying_loot, slot_id=index, address=self.object.char.address)

			if hasattr(self.object, "char"):
				# update missions that have collecting this item as requirement
				for mission in self.object.char.missions:
					if mission.state == MissionState.Active:
						for task in mission.tasks:
							if task.type == TaskType.ObtainItem and stack.lot in task.target:
								mission.increment_task(task, self.object)

		return stack

	def add_item_to_inventory_client_sync(self, address, bound:c_bit=False, bound_on_equip:c_bit=False,  bound_on_pickup:c_bit=False, loot_type_source:c_int=0, extra_info:"ldf"=None, object_template:c_int=None, subkey:c_int64=0, inv_type:c_int=0, amount:c_uint=1, item_total:c_uint=0, new_obj_id:c_int64=None, flying_loot_pos:Vector3=None, show_flying_loot:c_bit=True, slot_id:c_int=None):
		pass

	def remove_item_from_inv(self, inventory_type, item=None, object_id=0, lot=0, amount=1):
		if item is not None:
			object_id = item.object_id

		self.object._v_server.send_game_message(self.remove_item_from_inventory, inventory_type=inventory_type, extra_info={}, force_deletion=True, object_id=object_id, object_template=lot, stack_count=amount, address=self.object.char.address)

	def remove_item_from_inventory(self, address, confirmed:c_bit=True, delete_item:c_bit=True, out_success:c_bit=False, inventory_type:c_int=0, loot_type_source:c_int=0, extra_info:"ldf"=None, force_deletion:c_bit=False, loot_type_source_id:c_int64=0, object_id:c_int64=0, object_template:c_int=0, requesting_object_id:c_int64=0, stack_count:c_uint=1, stack_remaining:c_uint=0, subkey:c_int64=0, trade_id:c_int64=0):
		if confirmed:
			assert delete_item
			assert not out_success
			assert not extra_info
			assert loot_type_source_id == 0
			assert requesting_object_id == 0
			assert stack_remaining == 0
			assert subkey == 0
			assert trade_id == 0
			inventory = self.inventory_type_to_inventory(inventory_type)
			if object_id != 0:
				for item in inventory:
					if item is not None and item.object_id == object_id:
						break
			elif object_template != 0:
				for item in inventory:
					if item is not None and item.lot == object_template:
						break
			else:
				log.warning("Neither object id nor lot specified, can't remove item")
				return

			item.amount -= stack_count
			assert item.amount >= 0
			if item.amount == 0: # delete item
				if item.equipped:
					self.un_equip_inventory(address=None, item_to_unequip=item.object_id)

				if inventory_type in (InventoryType.Bricks, InventoryType.TempModels, InventoryType.MissionObjects):
					inventory.remove(item)
				else:
					inventory[inventory.index(item)] = None
				if hasattr(item, "module_lots"):
					for module_lot in item.module_lots:
						self.add_item_to_inventory(module_lot)

	def equip_inventory(self, address, ignore_cooldown:c_bit=False, out_success:c_bit=False, item_to_equip:c_int64=None):
		assert not out_success
		for inv in (self.items, self.models):
			for item in inv:
				if item is not None and item.object_id == item_to_equip:
					items = [i for i in inv if i is not None and i.equipped]
					for equipped_item in items: # unequip any items of the same type
						if equipped_item.item_type == item.item_type:
							self.un_equip_inventory(address=None, item_to_unequip=equipped_item.object_id)

					item.equipped = True
					self.equipped_items_flag = True
					self.object._serialize = True

					if hasattr(self.object, "char"):
						self.object.skill.add_skill_for_item(item)
					return

	def un_equip_inventory(self, address, even_if_dead:c_bit=False, ignore_cooldown:c_bit=False, out_success:c_bit=False, item_to_unequip:c_int64=None, replacement_object_id:c_int64=0):
		assert not out_success
		assert replacement_object_id == 0
		for inv in (self.items, self.models):
			for item in inv:
				if item is not None and item.object_id == item_to_unequip:
					item.equipped = False
					self.equipped_items_flag = True
					self.object._serialize = True

					if hasattr(self.object, "char"):
						self.object.skill.remove_skill_for_item(item)
					return

	def set_inventory_size(self, address, inventory_type:c_int=None, size:c_int=None):
		inv = self.inventory_type_to_inventory(inventory_type)
		inv.extend([None] * (size - len(inv)))

	def move_item_between_inventory_types(self, address, inventory_type_a:c_int=None, inventory_type_b:c_int=None, object_id:c_int64=None, show_flying_loot:c_bit=True, stack_count:c_uint=1, template_id:c_int=-1):
		source = self.inventory_type_to_inventory(inventory_type_a)
		for item in source:
			if item is not None and (item.object_id == object_id or item.lot == template_id):
				if stack_count == 0:
					move_stack_count = item.amount
				else:
					assert item.amount >= stack_count
					move_stack_count = stack_count
				new_item = self.add_item_to_inventory(item.lot, move_stack_count, inventory_type=inventory_type_b, show_flying_loot=show_flying_loot)
				self.remove_item_from_inv(inventory_type_a, item, amount=move_stack_count)
				return new_item
