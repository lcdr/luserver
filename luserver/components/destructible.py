from typing import Dict

from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import broadcast, c_int, Config, EB, EF, EO, EP, ES, GameObject, OBJ_NONE, Player, SpawnerObject, StatsObject
from ..world import server
from ..math.vector import Vector3
from .component import Component
from .mission import TaskType

class KillType:
	Violent = 0
	Silent = 1

class DestructibleComponent(Component):
	object: StatsObject

	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.comp_id = comp_id
		self.object.destructible = self

	def init(self, set_vars: Dict[str, object]) -> None:
		comp = server.db.destructible_component[self.comp_id]
		self.object.stats.faction = comp[0]
		self.death_rewards = comp[1]
		self.object.stats._max_life = comp[2]
		self.object.stats._max_armor = comp[3]
		self.object.stats._max_imagination = comp[4]
		self.object.stats.life = self.object.stats.max_life
		self.object.stats.armor = self.object.stats.max_armor
		self.object.stats.imagination = self.object.stats.max_imagination
		if "is_smashable" in set_vars:
			self.object.stats.is_smashable = set_vars["is_smashable"]
		else:
			self.object.stats.is_smashable = comp[5]
		self.spawn_group_on_smash = set_vars.get("spawn_group_on_smash", "")
		del self.comp_id

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

	def deal_damage(self, damage: int, dealer: GameObject) -> None:
		self.object.handle("hit", damage, dealer, silent=True)

		if damage > self.object.stats.armor:
			if damage >= self.object.stats.armor + self.object.stats.life:
				if isinstance(dealer, Player):
					loot_owner = dealer
				else:
					loot_owner = OBJ_NONE
				self.simply_die(killer=dealer, loot_owner=loot_owner)
			self.object.stats.life = max(0, self.object.stats.life - (damage - self.object.stats.armor))
		self.object.stats.armor = max(0, self.object.stats.armor - damage)

	def simply_die(self, death_type:str="", kill_type:c_int=KillType.Violent, killer:GameObject=OBJ_NONE, loot_owner:Player=OBJ_NONE) -> None:
		"""Shorthand for request_die with default values."""
		self.on_request_die(False, death_type, 0, 0, 10, kill_type, killer, loot_owner)

	def on_request_die(self, unknown_bool:bool=EB, death_type:str=ES, direction_relative_angle_xz:float=EF, direction_relative_angle_y:float=EF, direction_relative_force:float=EF, kill_type:c_int=KillType.Violent, killer:GameObject=EO, loot_owner:Player=EP) -> None:
		if self.object.stats.life == 0:
			# already dead
			return
		if self.object.stats.armor != 0:
			self.object.stats.armor = 0
		if self.object.stats.life != 0:
			self.object.stats.life = 0
		if self.object.stats.imagination != 0:
			self.object.stats.imagination = 0

		self.object.stats.die(False, True, death_type, direction_relative_angle_xz, direction_relative_angle_y, direction_relative_force, kill_type, killer, loot_owner)

		if killer and hasattr(killer, "char"):
			killer.char.mission.update_mission_task(TaskType.KillEnemy, self.object.lot)

		if loot_owner and hasattr(loot_owner, "char"):
			self.object.physics.drop_rewards(*self.death_rewards, loot_owner)

		if isinstance(self.object, Player):
			if server.world_id[0] % 100 == 0:
				coins_lost = min(10000, self.object.char.currency//100)
				if 100 > self.object.char.currency > 0:
					coins_lost = 1 # seems this is what the client does
				self.object.char.set_currency(currency=self.object.char.currency - coins_lost, loot_type=8, position=Vector3.zero)
			self.object.char.dismount()

			if server.world_control_object is not None and hasattr(server.world_control_object.script, "player_died"):
				server.world_control_object.script.player_died(player=self.object)
		else:
			if self.spawn_group_on_smash != "":
				for obj in server.get_objects_in_group(self.spawn_group_on_smash):
					if isinstance(obj, SpawnerObject):
						obj.spawner.spawn()

			if not hasattr(self.object, "comp_108"):
				if self.object.lot == 9632: # hardcode for property guard, generalize this somewhen
					self.object.call_later(5, lambda: server.replica_manager.destruct(self.object))
				else:
					server.replica_manager.destruct(self.object)

	@broadcast
	def resurrect(self, resurrect_immediately: bool=False) -> None:
		pass
