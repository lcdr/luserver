import logging

from bitstream import c_bit, c_float, c_int, c_uint, WriteStream
from ..game_object import broadcast, Config, EF, ES, EO, GameObject, OBJ_NONE, Player
from ..game_object import c_uint as c_uint_
from .component import Component

log = logging.getLogger(__name__)

class StatsSubcomponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
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
	def max_life(self) -> int:
		return self._max_life

	@max_life.setter
	def max_life(self, value: int) -> None:
		if value < 0:
			log.warning("Max life attempted to set to %i", value)

		self._max_life = max(0, value)
		if self.life > self.max_life:
			self.life = self.max_life

	@property
	def life(self) -> int:
		return self._life

	@life.setter
	def life(self, value: int) -> None:
		if value < 0:
			log.warning("Life attempted to set to %i", value)

		self._life = max(0, min(value, self.max_life))

	@property
	def max_armor(self) -> int:
		return self._max_armor

	@max_armor.setter
	def max_armor(self, value: int) -> None:
		if value < 0:
			log.warning("Max armor attempted to set to %i", value)

		self._max_armor = max(0, value)
		if self.armor > self.max_armor:
			self.armor = self.max_armor

	@property
	def armor(self) -> int:
		return self._armor

	@armor.setter
	def armor(self, value: int) -> None:
		if value < 0:
			log.warning("Armor attempted to set to %i", value)

		self._armor = max(0, min(value, self.max_armor))

	@property
	def max_imagination(self) -> int:
		return self._max_imagination

	@max_imagination.setter
	def max_imagination(self, value: int) -> None:
		if value < 0:
			log.warning("Max imagination attempted to set to %i", value)

		self._max_imagination = max(0, value)
		if self.imagination > self.max_imagination:
			self.imagination = self.max_imagination

	@property
	def imagination(self) -> int:
		return self._imagination

	@imagination.setter
	def imagination(self, value: int) -> None:
		if value < 0:
			log.warning("Imagination attempted to set to %i", value)

		self._imagination = max(0, min(value, self.max_imagination))

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if is_creation:
			out.write(c_bit(False))

		if self.flag("stats_flag", out, is_creation):
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

		out.write(c_bit(False))

	def on_destruction(self) -> None:
		if self.object.spawner_object is not None:
			self.object.spawner_object.handle("spawned_destruction")

	def refill_stats(self) -> None:
		self.life = self.max_life
		self.armor = self.max_armor
		self.imagination = self.max_imagination

	@broadcast
	def die(self, client_death:bool=False, spawn_loot:bool=True, death_type:str=ES, direction_relative_angle_xz:float=EF, direction_relative_angle_y:float=EF, direction_relative_force:float=EF, kill_type:c_uint_=0, killer:GameObject=EO, loot_owner:Player=OBJ_NONE) -> None:
		self.object.handle("death", killer, silent=True)
