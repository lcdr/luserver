class InventoryType:
	Items = 0
	Bricks = 2
	TempItems = 4
	Models = 5
	TempModels = 6
	Behaviors = 7
	# Properties = 8 ?
	# VendorSellSpace = 11
	MissionObjects = 12
	Max = -1 # not the correct value

class ItemType:
	Brick = 1
	Hat = 2
	Hair = 3
	Neck = 4
	LeftHand = 5
	RightHand = 6
	Pants = 7
	Behavior = 10
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
	Trade = 6
	# 8 occurs when deleting an item
	# loot drop = 11 ?
	# 16 occurs on completing modular build
	# 21 occurs with modular build temp models

import logging

from persistent import Persistent
from persistent.list import PersistentList

from ..bitstream import c_bit, c_int, c_int64, c_uint, c_ushort
from ..ldf import LDF, LDFDataType
from ..messages import broadcast, single, Serializable
from ..math.vector import Vector3
from .component import Component
from .mission import TaskType

log = logging.getLogger(__name__)

class Stack(Persistent, Serializable):
	def __init__(self, db, object_id, lot, amount=1):
		self.object_id = object_id
		self.lot = lot
		self.amount = amount
		self.slot = 0

		for component_type, component_id in db.components_registry[self.lot]:
			if component_type == 11: # ItemComponent, make an enum for this somewhen
				self.base_value = db.item_component[component_id][0]
				self.item_type = db.item_component[component_id][1]
				self.sub_items = db.item_component[component_id][3]
				break
		else:
			log.error("ItemComponent for LOT %i not found!", self.lot)

	def __repr__(self):
		return "%ix %i" % (self.amount, self.lot)

	def serialize(self, stream):
		stream.write(c_int64(self.object_id))
		stream.write(c_int(self.lot))
		stream.write(c_bit(False))
		stream.write(c_bit(self.amount != 1))
		if self.amount != 1:
			stream.write(c_uint(self.amount))
		stream.write(c_bit(self.slot != 0))
		if self.slot != 0:
			stream.write(c_ushort(self.slot))
		stream.write(c_bit(False))
		stream.write(c_bit(False))
		stream.write(c_bit(True))

	@staticmethod
	def deserialize(stream):
		item = Stack.__new__(Stack)
		item.object_id = stream.read(c_int64)
		item.lot = stream.read(c_int)
		if stream.read(c_bit):
			print("UNKNOWN1", stream.read(c_int64))
		if stream.read(c_bit):
			item.amount = stream.read(c_uint)
		else:
			item.amount = 1
		if stream.read(c_bit):
			item.slot = stream.read(c_ushort)
		else:
			item.slot = 0
		if stream.read(c_bit):
			print("UNKNOWN2", stream.read(c_uint))
		if stream.read(c_bit):
			raise NotImplementedError
			#ldf = LDF()
			#ldf.from_bitstream(stream)
		print("bit", stream.read(c_bit))
		print(item)
		return item

class ItemComponent(Component):
	def serialize(self, out, is_creation):
		out.write(c_bit(False))

class InventoryComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.inventory = self
		self.equipped_items_flag = False
		self.equipped = PersistentList()
		self.equipped.append(PersistentList()) # current equip state
		self.items = PersistentList([None]*20)
		self.bricks = PersistentList()
		self.temp_items = PersistentList()
		self.models = PersistentList([None]*200)
		self.behaviors = PersistentList([None]*200)
		self.temp_models = PersistentList()
		self.mission_objects = PersistentList()

		if comp_id in self.object._v_server.db.inventory_component:
			for item_lot, equip in self.object._v_server.db.inventory_component[comp_id]:
				item = self.add_item_to_inventory(item_lot, persistent=False, notify_client=False)
				if equip:
					self.equip_inventory(item_to_equip=item.object_id)

	def serialize(self, out, is_creation):
		out.write(c_bit(self.equipped_items_flag or is_creation))
		if self.equipped_items_flag or is_creation:
			out.write(c_uint(len(self.equipped[-1])))
			for item in self.equipped[-1]:
				item.serialize(out)
			self.equipped_items_flag = False
		out.write(c_bit(False))

	def inventory_type_to_inventory(self, inventory_type):
		if inventory_type == InventoryType.Items:
			return self.items
		if inventory_type == InventoryType.Bricks:
			return self.bricks
		if inventory_type == InventoryType.TempItems:
			return self.temp_items
		if inventory_type == InventoryType.Models:
			return self.models
		if inventory_type == InventoryType.TempModels:
			return self.temp_models
		if inventory_type == InventoryType.Behaviors:
			return self.behaviors
		if inventory_type == InventoryType.MissionObjects:
			return self.mission_objects
		raise NotImplementedError(inventory_type)

	def push_equipped_items_state(self):
		self.equipped.append(self.equipped[-1].copy())
		self.equipped_items_flag = True

	def pop_equipped_items_state(self):
		if len(self.equipped) == 1:
			return
		for equipped_item in self.equipped[-1]:
			self.un_equip_inventory(item_to_unequip=equipped_item.object_id)
		self.equipped.pop()
		self.equipped_items_flag = True

	def move_item_in_inventory(self, dest_inventory_type:c_int=0, object_id:c_int64=None, inventory_type:c_int=None, response_code:c_int=None, slot:c_int=None):
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
				item_type, stack_size = self.object._v_server.db.item_component[component_id][1:3]
				break
		else:
			raise ValueError("lot", lot)
			# no item component found


		if hasattr(self.object, "char"):
			self.object.char.update_mission_task(TaskType.ObtainItem, lot, increment=amount)

		if inventory_type is None:
			if item_type == ItemType.Brick:
				inventory_type = InventoryType.Bricks
			elif item_type in (ItemType.Hat, ItemType.Hair, ItemType.Neck, ItemType.LeftHand, ItemType.RightHand, ItemType.Pants, ItemType.SomeOtherKindOfMissionObject, ItemType.Consumable, ItemType.Chest, ItemType.Package, ItemType.Mount):
				inventory_type = InventoryType.Items
			elif item_type == ItemType.Behavior:
				inventory_type = InventoryType.Behaviors
			elif item_type == ItemType.MissionObject:
				inventory_type = InventoryType.MissionObjects
			elif item_type in (ItemType.Model, ItemType.Vehicle):
				inventory_type = InventoryType.Models
			else:
				raise NotImplementedError(lot, item_type)
		inventory = self.inventory_type_to_inventory(inventory_type)

		while amount > 0:
			new_stack = stack_size == 1
			if not new_stack:
				for stack in inventory:
					if stack is not None and stack.lot == lot and stack.amount < stack_size:
						added_amount = min(stack_size - stack.amount, amount)
						stack.amount += added_amount
						amount -= added_amount
						index = inventory.index(stack)
						break
				else:
					new_stack = True

			if new_stack:
				if persistent:
					object_id = self.object._v_server.new_object_id()
				else:
					object_id = self.object._v_server.new_spawned_id()

				added_amount = min(stack_size, amount)
				amount -= added_amount
				stack = Stack(self.object._v_server.db, object_id, lot, added_amount)
				if module_lots:
					stack.module_lots = module_lots

				if inventory_type in (InventoryType.Bricks, InventoryType.TempItems, InventoryType.TempModels, InventoryType.MissionObjects):
					inventory.append(stack)
					index = len(inventory)-1
				else:
					for index, item in enumerate(inventory):
						if item is None:
							inventory[index] = stack
							break
					else:
						log.info("no space left, sending item by mail")
						self.object._v_server.mail.send_mail("%[MAIL_SYSTEM_NOTIFICATION]", "%[MAIL_ACHIEVEMENT_OVERFLOW_HEADER]", "%[MAIL_ACHIEVEMENT_OVERFLOW_BODY]", self.object, stack)
						continue

			if hasattr(self.object, "char") and notify_client:
				extra_info = LDF()
				if hasattr(stack, "module_lots"):
					extra_info.ldf_set("assemblyPartLOTs", LDFDataType.STRING, [(LDFDataType.INT32, i) for i in stack.module_lots])

				self.add_item_to_inventory_client_sync(bound=True, bound_on_equip=True, bound_on_pickup=True, loot_type_source=source_type, extra_info=extra_info, object_template=stack.lot, inv_type=inventory_type, amount=added_amount, new_obj_id=stack.object_id, flying_loot_pos=Vector3.zero, show_flying_loot=show_flying_loot, slot_id=index)
		return stack

	@single
	def add_item_to_inventory_client_sync(self, bound:c_bit=False, bound_on_equip:c_bit=False,  bound_on_pickup:c_bit=False, loot_type_source:c_int=0, extra_info:LDF=None, object_template:c_int=None, subkey:c_int64=0, inv_type:c_int=0, amount:c_uint=1, item_total:c_uint=0, new_obj_id:c_int64=None, flying_loot_pos:Vector3=None, show_flying_loot:c_bit=True, slot_id:c_int=None):
		pass

	def remove_item_from_inv(self, inventory_type, item=None, object_id=0, lot=0, amount=1):
		if item is not None:
			object_id = item.object_id

		if hasattr(self.object, "char"):
			self.remove_item_from_inventory(inventory_type=inventory_type, extra_info=LDF(), force_deletion=True, object_id=object_id, object_template=lot, stack_count=amount)

	@single
	def remove_item_from_inventory(self, confirmed:c_bit=True, delete_item:c_bit=True, out_success:c_bit=False, inventory_type:c_int=InventoryType.Max, loot_type_source:c_int=0, extra_info:LDF=None, force_deletion:c_bit=False, loot_type_source_id:c_int64=0, object_id:c_int64=0, object_template:c_int=0, requesting_object_id:c_int64=0, stack_count:c_uint=1, stack_remaining:c_uint=0, subkey:c_int64=0, trade_id:c_int64=0):
		if not confirmed:
			return
		if object_id == 0 and object_template == 0:
			log.warning("Neither object id nor lot specified, can't remove item")
			return
		assert delete_item
		assert not out_success
		assert not extra_info
		assert loot_type_source_id == 0
		assert requesting_object_id == 0
		assert stack_remaining == 0
		assert subkey == 0
		assert trade_id == 0
		if inventory_type == InventoryType.Max:
			inventories = [InventoryType.Items, InventoryType.Models, InventoryType.MissionObjects]
		else:
			inventories = [inventory_type]
		for inventory_type in inventories:
			inventory = self.inventory_type_to_inventory(inventory_type)
			if object_id != 0:
				for item in inventory:
					if item is not None and item.object_id == object_id:
						break
				else:
					continue
			elif object_template != 0:
				for item in inventory:
					if item is not None and item.lot == object_template:
						break
				else:
					continue

			item.amount -= stack_count
			assert item.amount >= 0
			if item.amount == 0: # delete item
				if item in self.equipped[-1]:
					self.un_equip_inventory(item_to_unequip=item.object_id)

				if inventory_type in (InventoryType.Bricks, InventoryType.TempItems, InventoryType.TempModels, InventoryType.MissionObjects):
					inventory.remove(item)
				else:
					inventory[inventory.index(item)] = None
				if hasattr(item, "module_lots") and not force_deletion: # only give modules if the player removed it
					for module_lot in item.module_lots:
						self.add_item_to_inventory(module_lot)
			return

	def equip_inventory(self, ignore_cooldown:c_bit=False, out_success:c_bit=False, item_to_equip:c_int64=None):
		assert not out_success
		for inv in (self.items, self.temp_items, self.models):
			for item in inv:
				if item is not None and item.object_id == item_to_equip:
					# unequip any items of the same type
					for inv in (self.items, self.temp_items, self.models):
						for other_item in inv:
							if other_item is not None and other_item in self.equipped[-1] and other_item.item_type == item.item_type:
								self.un_equip_inventory(item_to_unequip=other_item.object_id)

					# equip sub-items
					for sub_item in item.sub_items:
						sub = self.add_item_to_inventory(sub_item, inventory_type=InventoryType.TempItems)
						self.equip_inventory(item_to_equip=sub.object_id)

					self.equipped[-1].append(item)
					self.equipped_items_flag = True
					self.object._serialize = True

					if hasattr(self.object, "char"):
						self.object.skill.add_skill_for_item(item)

						for set_items, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in self.object._v_server.db.item_sets:
							if item.lot in set_items:
								for set in (skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6):
									for skill in set:
										self.object.skill.add_skill_server(skill)
					return

	def un_equip_inventory(self, even_if_dead:c_bit=False, ignore_cooldown:c_bit=False, out_success:c_bit=False, item_to_unequip:c_int64=None, replacement_object_id:c_int64=0):
		assert not out_success
		assert replacement_object_id == 0
		for item in self.equipped[-1]:
			if item.object_id == item_to_unequip:
				self.equipped[-1].remove(item)
				self.equipped_items_flag = True
				self.object._serialize = True

				for sub_item in item.sub_items:
					self.remove_item_from_inv(InventoryType.TempItems, lot=sub_item)

				if hasattr(self.object, "char"):
					self.object.skill.remove_skill_for_item(item)

					for set_items, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in self.object._v_server.db.item_sets:
						if item.lot in set_items:
							for set in (skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6):
								for skill in set:
									self.object.skill.remove_skill_server(skill)

				# if this is a sub-item of another item, unequip the other item (and its sub-items)
				for inv in (self.items, self.temp_items, self.models):
					for other_item in inv:
						if other_item is not None and other_item in self.equipped[-1] and item.lot in other_item.sub_items:
							self.un_equip_inventory(item_to_unequip=other_item.object_id)

	@broadcast
	def set_inventory_size(self, inventory_type:c_int=None, size:c_int=None):
		inv = self.inventory_type_to_inventory(inventory_type)
		inv.extend([None] * (size - len(inv)))

	def move_item_between_inventory_types(self, inventory_type_a:c_int=None, inventory_type_b:c_int=None, object_id:c_int64=None, show_flying_loot:c_bit=True, stack_count:c_uint=1, template_id:c_int=-1):
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
