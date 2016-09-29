import asyncio
import random

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..math.vector import Vector3
from .component import Component

class StatsSubcomponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.stats = self
		self._flags["_max_life"] = "stats_flag"
		self._flags["_max_armor"] = "stats_flag"
		self._flags["_max_imagination"] = "stats_flag"
		self._flags["life"] = "stats_flag"
		self._flags["armor"] = "stats_flag"
		self._flags["imagination"] = "stats_flag"
		self._flags["faction"] = "stats_flag"
		if not hasattr(self.object, "destructible"):
			self._max_life = 1
			self._max_armor = 0
			self._max_imagination = 0
			self.life = self.max_life
			self.armor = self.max_armor
			self.imagination = self.max_imagination
			self.faction = -1
			self.is_smashable = False
		else:
			self.object.destructible.init()

	@property
	def max_life(self):
		return self._max_life

	@max_life.setter
	def max_life(self, value):
		self._max_life = value
		if self.life > self.max_life:
			self.life = self.max_life

	@property
	def life(self):
		return self._life

	@life.setter
	def life(self, value):
		self._life = max(0, min(value, self.max_life))

	@property
	def max_armor(self):
		return self._max_armor

	@max_armor.setter
	def max_armor(self, value):
		self._max_armor = value
		if self.armor > self.max_armor:
			self.armor = self.max_armor

	@property
	def armor(self):
		return self._armor

	@armor.setter
	def armor(self, value):
		self._armor = max(0, min(value, self.max_armor))

	@property
	def max_imagination(self):
		return self._max_imagination

	@max_imagination.setter
	def max_imagination(self, value):
		self._max_imagination = value
		if self.imagination > self.max_imagination:
			self.imagination = self.max_imagination

	@property
	def imagination(self):
		return self._imagination

	@imagination.setter
	def imagination(self, value):
		self._imagination = max(0, min(value, self.max_imagination))

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))

		out.write(c_bit(self.stats_flag or is_creation))
		if self.stats_flag or is_creation:
			out.write(c_uint(self.life))
			out.write(c_float(self.max_life))
			out.write(c_uint(self.armor))
			out.write(c_float(self.max_armor))
			out.write(c_uint(self.imagination))
			out.write(c_float(self.max_imagination))
			out.write(c_uint(0))
			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_float(self.max_life))
			out.write(c_float(self.max_armor))
			out.write(c_float(self.max_imagination))
			out.write(c_uint(1))
			out.write(c_int(self.faction))
			out.write(c_bit(self.is_smashable))
			if is_creation:
				out.write(c_bit(False))
				out.write(c_bit(False))
				if self.is_smashable:
					out.write(c_bit(False))
					out.write(c_bit(False))

			self.stats_flag = False

		out.write(c_bit(False))

	def on_destruction(self):
		if self.object.spawner_object is not None:
				asyncio.get_event_loop().call_later(8, self.object.spawner_object.spawner.spawn)

	def random_loot(self, loot_matrix, owner):
		# ridiculously bad and biased temporary implementation, please fix
		loot = []
		for loot_table, percent, min_to_drop, max_to_drop in loot_matrix:
			lot, _ = random.choice(loot_table)
			loot.append(lot)
		return loot

	def drop_rewards(self, loot_matrix, currency_min, currency_max, owner):
		if currency_min is not None and currency_max is not None:
			currency = random.randint(currency_min, currency_max)
			self.object._v_server.send_game_message(owner.char.drop_client_loot, currency=currency, item_template=-1, loot_id=0, owner=owner.object_id, source_obj=self.object.object_id, address=owner.char.address)

		if loot_matrix is not None:
			loot = self.random_loot(loot_matrix, owner)
			for lot in loot:
				self.drop_loot(lot, owner)

	def drop_loot(self, lot, owner):
		loot_position = Vector3(self.object.physics.position.x+(random.random()-0.5)*20, self.object.physics.position.y, self.object.physics.position.z+(random.random()-0.5)*20)
		object_id = self.object._v_server.new_spawned_id()
		self.object._v_server.dropped_loot.setdefault(owner.object_id, {})[object_id] = lot
		self.object._v_server.send_game_message(owner.char.drop_client_loot, use_position=True, spawn_position=self.object.physics.position, final_position=loot_position, currency=0, item_template=lot, loot_id=object_id, owner=owner.object_id, source_obj=self.object.object_id, address=owner.char.address)

	def die(self, address, client_death:c_bit=False, spawn_loot:c_bit=True, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_uint=0, killer_id:c_int64=None, loot_owner_id:c_int64=0):
		pass
