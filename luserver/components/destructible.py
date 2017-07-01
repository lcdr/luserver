from ..bitstream import c_bit, c_int, c_int64
from ..messages import broadcast
from ..world import server
from ..math.vector import Vector3
from .component import Component
from .mission import TaskType

class DestructibleComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.comp_id = comp_id
		self.object.destructible = self

	def init(self, set_vars):
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
		del self.comp_id

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

	def deal_damage(self, damage, dealer):
		self.object.handle("on_hit", damage, dealer, silent=True)

		if damage > self.object.stats.armor:
			self.object.stats.life = max(0, self.object.stats.life - (damage - self.object.stats.armor))
		self.object.stats.armor = max(0, self.object.stats.armor - damage)

		if self.object.stats.life == 0:
			self.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=dealer.object_id, loot_owner_id=dealer.object_id)

	def request_die(self, unknown_bool:bool=None, death_type:str=None, direction_relative_angle_xz:float=None, direction_relative_angle_y:float=None, direction_relative_force:float=None, kill_type:c_int=0, killer_id:c_int64=None, loot_owner_id:c_int64=None):
		if self.object.stats.armor != 0:
			self.object.stats.armor = 0
		if self.object.stats.life != 0:
			self.object.stats.life = 0
		if self.object.stats.imagination != 0:
			self.object.stats.imagination = 0

		self.object.send_game_message("die", False, True, death_type, direction_relative_angle_xz, direction_relative_angle_y, direction_relative_force, kill_type, killer_id, loot_owner_id)

		killer = server.get_object(killer_id)
		if killer and hasattr(killer, "char"):
			killer.char.update_mission_task(TaskType.KillEnemy, self.object.lot)

		loot_owner = server.get_object(loot_owner_id)
		if loot_owner and hasattr(loot_owner, "char"):
			self.object.physics.drop_rewards(*self.death_rewards, loot_owner)

		if hasattr(self.object, "char"):
			if server.world_id[0] % 100 == 0:
				coins_lost = min(10000, self.object.char.currency//100)
				self.object.char.set_currency(currency=self.object.char.currency - coins_lost, loot_type=8, position=Vector3.zero)
			self.object.char.dismount()

			if server.world_control_object is not None and hasattr(server.world_control_object.script, "player_died"):
				server.world_control_object.script.player_died(player=self.object)
		else:
			if not hasattr(self.object, "comp_108"):
				if self.object.lot == 9632: # hardcode for property guard, generalize this somewhen
					self.object.call_later(5, lambda: server.destruct(self.object))
				else:
					server.destruct(self.object)

	@broadcast
	def resurrect(self, resurrect_immediately=False):
		pass
