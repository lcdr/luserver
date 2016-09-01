import asyncio
import random

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..math.vector import Vector3

class StatsSubcomponent:
	def __init__(self, comp_id):
		self._flags["life"] = "stats_flag"
		self._flags["armor"] = "stats_flag"
		self._flags["imagination"] = "stats_flag"
		self._flags["faction"] = "stats_flag"
		if not hasattr(self, "faction"): # if this stuff hasn't already been assigned by DestructibleComponent
			self.faction = -1
			self._max_life = 1
			self._max_armor = 0
			self._max_imagination = 0
			self.life = self.max_life
			self.armor = self.max_armor
			self.imagination = self.max_imagination
			self.is_smashable = False

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
		if self.spawner is not None:
				asyncio.get_event_loop().call_later(8, self.spawner.spawn)

	def drop_loot(self, lot, owner):
		object_id = self._v_server.new_spawned_id()
		self._v_server.dropped_loot.setdefault(owner.object_id, {})[object_id] = lot
		self._v_server.send_game_message(owner.drop_client_loot, use_position=True, spawn_position=self.position, final_position=Vector3(self.position.x+(random.random()-0.5)*20, self.position.y, self.position.z+(random.random()-0.5)*20), currency=0, item_template=lot, loot_id=object_id, owner=owner.object_id, source_obj=self.object_id, address=owner.address)

	def die(self, address, client_death:c_bit=False, spawn_loot:c_bit=True, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_uint=0, killer_id:c_int64=None, loot_owner_id:c_int64=0):
		pass
