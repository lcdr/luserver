import logging

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..game_object import GameObject
from ..messages import broadcast
from .component import Component

log = logging.getLogger(__name__)

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
			self.object.destructible.init(set_vars)

	@property
	def max_life(self):
		return self._max_life

	@max_life.setter
	def max_life(self, value):
		if value < 0:
			log.warning("Max life attempted to set to %i", value)

		self._max_life = max(0, value)
		if self.life > self.max_life:
			self.life = self.max_life

	@property
	def life(self):
		return self._life

	@life.setter
	def life(self, value):
		if value < 0:
			log.warning("Life attempted to set to %i", value)

		self._life = max(0, min(value, self.max_life))

	@property
	def max_armor(self):
		return self._max_armor

	@max_armor.setter
	def max_armor(self, value):
		if value < 0:
			log.warning("Max armor attempted to set to %i", value)

		self._max_armor = max(0, value)
		if self.armor > self.max_armor:
			self.armor = self.max_armor

	@property
	def armor(self):
		return self._armor

	@armor.setter
	def armor(self, value):
		if value < 0:
			log.warning("Armor attempted to set to %i", value)

		self._armor = max(0, min(value, self.max_armor))

	@property
	def max_imagination(self):
		return self._max_imagination

	@max_imagination.setter
	def max_imagination(self, value):
		if value < 0:
			log.warning("Max imagination attempted to set to %i", value)

		self._max_imagination = max(0, value)
		if self.imagination > self.max_imagination:
			self.imagination = self.max_imagination

	@property
	def imagination(self):
		return self._imagination

	@imagination.setter
	def imagination(self, value):
		if value < 0:
			log.warning("Imagination attempted to set to %i", value)

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
			self.object.spawner_object.handle("on_spawned_destruction")

	@broadcast
	def die(self, client_death:bool=False, spawn_loot:bool=True, death_type:str=None, direction_relative_angle_xz:float=None, direction_relative_angle_y:float=None, direction_relative_force:float=None, kill_type:c_uint=0, killer:GameObject=None, loot_owner:GameObject=0):
		self.object.handle("on_death", killer, silent=True)
