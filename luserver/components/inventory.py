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
	Mail = 3
	Achievement = 5
	Trade = 6
	# 8 occurs when deleting an item and when a player dies
	# loot drop = 11 ?
	# 13 related to build
	# 16 occurs on completing modular build
	# 18 occurs when opening a package item
	# 21 occurs with modular build temp models

import logging
from typing import List, Optional, Tuple

from persistent import Persistent
from persistent.list import PersistentList

from pyraknet.bitstream import c_bit, c_int, c_int64, c_uint, c_ushort, ReadStream, Serializable, WriteStream
from ..commonserver import ServerDB
from ..game_object import broadcast, Config, EI, EL, EV, GameObject, ObjectID, single
from ..game_object import c_int as c_int_
from ..game_object import c_int64 as c_int64_
from ..game_object import c_uint as c_uint_
from ..ldf import LDF, LDFDataType
from ..world import server
from ..math.vector import Vector3
from .component import Component
from .mission import TaskType

log = logging.getLogger(__name__)

class Stack(Persistent, Serializable):
	def __init__(self, db: ServerDB, object_id: ObjectID, lot: int, count: int=1):
		self.object_id = object_id
		self.lot = lot
		self.count = count
		self.slot = 0

		for component_type, component_id in db.components_registry[self.lot]:
			if component_type == 11: # ItemComponent, make an enum for this somewhen
				self.base_value = db.item_component[component_id][0]
				self.item_type = db.item_component[component_id][1]
				self.sub_items = db.item_component[component_id][3]
				break
		else:
			log.error("ItemComponent for LOT %i not found!", self.lot)

	def __repr__(self) -> str:
		return "%ix %i" % (self.count, self.lot)

	def serialize(self, stream: WriteStream) -> None:
		stream.write(c_int64(self.object_id))
		stream.write(c_int(self.lot))
		stream.write(c_bit(False))
		stream.write(c_bit(self.count != 1))
		if self.count != 1:
			stream.write(c_uint(self.count))
		stream.write(c_bit(self.slot != 0))
		if self.slot != 0:
			stream.write(c_ushort(self.slot))
		stream.write(c_bit(False))
		stream.write(c_bit(False))
		stream.write(c_bit(True))

	@staticmethod
	def deserialize(stream: ReadStream) -> "Stack":
		item = Stack.__new__(Stack)
		item.object_id = stream.read(c_int64)
		item.lot = stream.read(c_int)
		if stream.read(c_bit):
			print("UNKNOWN1", stream.read(c_int64))
		if stream.read(c_bit):
			item.count = stream.read(c_uint)
		else:
			item.count = 1
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
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))

class InventoryComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.inventory = self
		self._flags["equipped"] = "equipped_items_flag"
		self.equipped: List[List[Stack]] = PersistentList()
		self.equipped.append(PersistentList()) # current equip state
		self.attr_changed("equipped")
		self.items: List[Optional[Stack]] = PersistentList([None]*20)
		self.bricks: List[Stack] = PersistentList()
		self.temp_items: List[Stack] = PersistentList()
		self.models: List[Optional[Stack]] = PersistentList([None]*200)
		self.behaviors: List[Optional[Stack]] = PersistentList([None]*200)
		self.temp_models: List[Stack] = PersistentList()
		self.mission_objects: List[Stack] = PersistentList()

		if comp_id in server.db.inventory_component:
			for item_lot, equip in server.db.inventory_component[comp_id]:
				item = self.add_item(item_lot, persistent=False, notify_client=False)
				if equip:
					self.on_equip_inventory(item_to_equip=item.object_id)

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("equipped_items_flag", out, is_creation):
			out.write(c_uint(len(self.equipped[-1])))
			for item in self.equipped[-1]:
				out.write(item)
		out.write(c_bit(False))

	def inventory_type_to_inventory(self, inventory_type: int) -> List[Optional[Stack]]:
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

	def push_equipped_items_state(self) -> None:
		self.equipped.append(self.equipped[-1].copy())
		self.attr_changed("equipped")

	def on_pop_equipped_items_state(self) -> None:
		if len(self.equipped) == 1:
			return

		log.debug("previous: %s", self.equipped[-2])
		log.debug("current: %s", self.equipped[-1])

		# check for previously equipped items that have been unequipped or replaced
		for prev_equipped_item in self.equipped[-2]:
			if prev_equipped_item.count == 0:
				continue # item has been deleted

			for equipped_item in self.equipped[-1]:
				if equipped_item.item_type == prev_equipped_item.item_type:
					if equipped_item.lot != prev_equipped_item.lot:
						# item has been replaced, equip old item
						self.on_equip_inventory(item_to_equip=prev_equipped_item.object_id)
					break
			else:
				# item has been unequipped without replacement, equip again
				self.on_equip_inventory(item_to_equip=prev_equipped_item.object_id)

		# check for newly equipped items that weren't equipped previously
		for equipped_item in self.equipped[-1]:
			for prev_equipped_item in self.equipped[-2]:
				if equipped_item.item_type == prev_equipped_item.item_type:
					break
			else:
				# item should be unequipped
				self.on_un_equip_inventory(item_to_unequip=equipped_item.object_id)

		del self.equipped[-2]
		self.attr_changed("equipped")

	def on_move_item_in_inventory(self, dest_inventory_type:c_int_=0, object_id:c_int64_=EI, inventory_type:c_int_=EI, response_code:c_int_=EI, slot:c_int_=EI) -> None:
		assert dest_inventory_type == 0
		assert object_id != 0
		assert response_code == 0
		inventory = self.inventory_type_to_inventory(inventory_type)

		for item in inventory:
			if item is not None and item.object_id == object_id:
				inventory[inventory.index(item)] = inventory[slot]
				inventory[slot] = item
				break

	def add_item(self, lot: int, count: int=1, module_lots: Tuple[int, int, int]=None, inventory_type: int=None, source_type: int=0, show_flying_loot: bool=True, persistent: bool=True, notify_client: bool=True) -> Stack:
		for component_type, component_id in server.db.components_registry[lot]:
			if component_type == 11: # ItemComponent, make an enum for this somewhen
				item_type, stack_size = server.db.item_component[component_id][1:3]
				break
		else:
			raise ValueError("lot", lot)
			# no item component found


		if hasattr(self.object, "char"):
			self.object.char.mission.update_mission_task(TaskType.ObtainItem, lot, increment=count)

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

		if module_lots:
			stack_size = 1

		while count > 0:
			new_stack = stack_size == 1
			if not new_stack:
				for stack in inventory:
					if stack is not None and stack.lot == lot and (stack_size == 0 or stack.count < stack_size):
						if stack_size == 0:
							added_count = count
						else:
							added_count = min(stack_size - stack.count, count)
						stack.count += added_count
						count -= added_count
						index = inventory.index(stack)
						break
				else:
					new_stack = True

			if new_stack:
				if persistent:
					object_id = server.new_object_id()
				else:
					object_id = server.new_spawned_id()

				if stack_size == 0:
					added_count = count
				else:
					added_count = min(stack_size, count)
				count -= added_count
				stack = Stack(server.db, object_id, lot, added_count)
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
						server.mail.send_mail("%[MAIL_SYSTEM_NOTIFICATION]", "%[MAIL_ACHIEVEMENT_OVERFLOW_HEADER]", "%[MAIL_ACHIEVEMENT_OVERFLOW_BODY]", self.object, stack)
						continue

			if hasattr(self.object, "char") and notify_client:
				extra_info = LDF()
				if hasattr(stack, "module_lots"):
					extra_info.ldf_set("assemblyPartLOTs", LDFDataType.STRING, [(LDFDataType.INT32, i) for i in stack.module_lots])

				self.add_item_to_inventory_client_sync(loot_type_source=source_type, extra_info=extra_info, object_template=stack.lot, inv_type=inventory_type, count=added_count, new_obj_id=stack.object_id, flying_loot_pos=Vector3.zero, show_flying_loot=show_flying_loot, slot_id=index)
		return stack

	@single
	def add_item_to_inventory_client_sync(self, bound:bool=False, bound_on_equip:bool=False, bound_on_pickup:bool=False, loot_type_source:c_int_=0, extra_info:LDF=EL, object_template:c_int_=EI, subkey:c_int64_=0, inv_type:c_int_=0, count:c_uint_=1, item_total:c_uint_=0, new_obj_id:c_int64_=EI, flying_loot_pos:Vector3=EV, show_flying_loot:bool=True, slot_id:c_int_=EI) -> None:
		pass

	def remove_item(self, inventory_type: int, item: Stack=None, object_id: ObjectID=ObjectID(0), lot: int=0, count: int=1) -> Optional[Stack]:
		if item is not None:
			object_id = item.object_id

		if hasattr(self.object, "char"):
			return self.remove_item_from_inventory(inventory_type=inventory_type, extra_info=LDF(), force_deletion=True, object_id=object_id, object_template=lot, stack_count=count)

	@single
	def remove_item_from_inventory(self, confirmed:bool=True, delete_item:bool=True, out_success:bool=False, inventory_type:c_int_=InventoryType.Max, loot_type_source:c_int_=0, extra_info:LDF=EL, force_deletion:bool=False, loot_type_source_id:c_int64_=0, object_id:c_int64_=0, object_template:c_int_=0, requesting_object_id:c_int64_=0, stack_count:c_uint_=1, stack_remaining:c_uint_=0, subkey:c_int64_=0, trade_id:c_int64_=0) -> Optional[Stack]:
		if not confirmed:
			return
		if object_id == 0 and object_template == 0:
			log.error("Neither object id nor lot specified, can't remove item")
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
			inventories = [InventoryType.Items, InventoryType.Bricks, InventoryType.Models, InventoryType.MissionObjects]
		else:
			inventories = [inventory_type]

		last_affected_item = None
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

			item.count -= stack_count
			last_affected_item = item
			assert item.count >= 0
			if item.count == 0: # delete item
				if item in self.equipped[-1]:
					self.on_un_equip_inventory(item_to_unequip=item.object_id)

				if inventory_type in (InventoryType.Bricks, InventoryType.TempItems, InventoryType.TempModels, InventoryType.MissionObjects):
					inventory.remove(item)
				else:
					inventory[inventory.index(item)] = None
				if hasattr(item, "module_lots") and not force_deletion: # only give modules if the player removed it
					for module_lot in item.module_lots:
						self.add_item(module_lot)
			return last_affected_item

	def on_equip_inventory(self, ignore_cooldown:bool=False, out_success:bool=False, item_to_equip:c_int64_=EI) -> None:
		assert not out_success
		for inv in (self.items, self.temp_items, self.models):
			for item in inv:
				if item is not None and item.object_id == item_to_equip:
					self.equipped[-1].append(item)
					self.attr_changed("equipped")

					if hasattr(self.object, "char"):
						self.object.skill.add_skill_for_item(item)

						for set_items, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in server.db.item_sets:
							if item.lot in set_items:
								set_items_equipped = 0
								for eq_item in self.equipped[-1]:
									if eq_item.lot in set_items:
										set_items_equipped += 1
								if set_items_equipped == 2:
									set = skill_set_with_2
								elif set_items_equipped == 3:
									set = skill_set_with_3
								elif set_items_equipped == 4:
									set = skill_set_with_4
								elif set_items_equipped == 5:
									set = skill_set_with_5
								if set_items_equipped == 6:
									set = skill_set_with_6
								if 2 <= set_items_equipped <= 6:
									for skill in set:
										self.object.skill.add_skill_server(skill)

					# equip sub-items
					for sub_item in item.sub_items:
						sub = self.add_item(sub_item, inventory_type=InventoryType.TempItems)
						self.on_equip_inventory(item_to_equip=sub.object_id)

					# unequip any items of the same type
					for other_item in self.equipped[-1]:
						if other_item.item_type == item.item_type and other_item.object_id != item.object_id:
							self.on_un_equip_inventory(item_to_unequip=other_item.object_id)
							break

					# if this is a rocket, check for launchpads nearby, and possibly activate the launch sequence
					if item.lot == 6416 and self.object.char.traveling_rocket is None:
						for obj in server.world_data.objects.values():
							if hasattr(obj, "launchpad"):
								if self.object.physics.position.sq_distance(obj.physics.position) < 25:
									obj.launchpad.launch(self.object, item)
									break
					return

	def on_un_equip_inventory(self, even_if_dead:bool=False, ignore_cooldown:bool=False, out_success:bool=False, item_to_unequip:c_int64_=EI, replacement_object_id:c_int64_=0) -> None:
		assert not out_success
		assert replacement_object_id == 0
		for item in self.equipped[-1]:
			if item.object_id == item_to_unequip:
				self.equipped[-1].remove(item)
				self.attr_changed("equipped")

				if hasattr(self.object, "char"):
					self.object.skill.remove_skill_for_item(item)

					for set_items, skill_set_with_2, skill_set_with_3, skill_set_with_4, skill_set_with_5, skill_set_with_6 in server.db.item_sets:
						if item.lot in set_items:
							set_items_equipped = 1
							for eq_item in self.equipped[-1]:
								if eq_item.lot in set_items:
									set_items_equipped += 1
							if set_items_equipped == 2:
								set = skill_set_with_2
							elif set_items_equipped == 3:
								set = skill_set_with_3
							elif set_items_equipped == 4:
								set = skill_set_with_4
							elif set_items_equipped == 5:
								set = skill_set_with_5
							if set_items_equipped == 6:
								set = skill_set_with_6
							if 2 <= set_items_equipped <= 6:
								for skill in set:
									self.object.skill.remove_skill_server(skill)

				for sub_item in item.sub_items:
					self.remove_item(InventoryType.TempItems, lot=sub_item)

				# if this is a sub-item of another item, unequip the other item (and its sub-items)
				for other_item in self.equipped[-1]:
					if item.lot in other_item.sub_items:
						self.on_un_equip_inventory(item_to_unequip=other_item.object_id)
				break

	@broadcast
	def set_inventory_size(self, inventory_type:c_int_=EI, size:c_int_=EI) -> None:
		inv = self.inventory_type_to_inventory(inventory_type)
		inv.extend([None] * (size - len(inv)))

	def on_move_item_between_inventory_types(self, inventory_type_a:c_int_=EI, inventory_type_b:c_int_=EI, object_id:c_int64_=EI, show_flying_loot:bool=True, stack_count:c_uint_=1, template_id:c_int_=-1) -> Stack:
		source = self.inventory_type_to_inventory(inventory_type_a)
		for item in source:
			if item is not None and (item.object_id == object_id or item.lot == template_id):
				if stack_count == 0:
					move_stack_count = item.count
				else:
					assert item.count >= stack_count
					move_stack_count = stack_count
				new_item = self.add_item(item.lot, move_stack_count, inventory_type=inventory_type_b, show_flying_loot=show_flying_loot)
				self.remove_item(inventory_type_a, item, count=move_stack_count)
				return new_item

	def has_item(self, inventory_type: int, lot: int) -> bool:
		inv = self.inventory_type_to_inventory(inventory_type)
		for item in inv:
			if item is not None and item.lot == lot:
				return True
		return False

	def get_stack(self, inventory_type: int, object_id: ObjectID) -> Stack:
		inv = self.inventory_type_to_inventory(inventory_type)
		for item in inv:
			if item is not None and item.object_id == object_id:
				return item
		raise RuntimeError("Stack %i not found in inv %i" % (object_id, inventory_type))
