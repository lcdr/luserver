import random

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from ..math.vector import Vector3
from .comp108 import Comp108Component
from .mission import MissionState, TaskType
from .stats import StatsSubcomponent

class DestructibleComponent:
	def __init__(self, comp_id):
		StatsSubcomponent.__init__(self, comp_id)
		comp = self._v_server.db.destructible_component[comp_id]
		self.faction = comp[0]
		self.loot_matrix = comp[1]
		self.currency_min = comp[2]
		self.currency_max = comp[3]
		self._max_life = comp[4]
		self._max_armor = comp[5]
		self._max_imagination = comp[6]
		self.life = self.max_life
		self.armor = self.max_armor
		self.imagination = self.max_imagination

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

	def deal_damage(self, damage, dealer):
		self.armor = max(0, self.armor - damage)
		if self.armor - damage < 0:
			self.life += self.armor - damage
		if self.life <= 0:
			self.request_die(None, unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=dealer.object_id, loot_owner_id=dealer.object_id)

	def random_currency_amount(self):
		return random.randint(self.currency_min, self.currency_max)

	def random_loot(self):
		# ridiculously bad and biased temporary implementation, please fix
		loot = []
		for loot_table, percent, min_to_drop, max_to_drop in self.loot_matrix:
			lot, _ = random.choice(loot_table)
			loot.append(lot)
		return loot

	def drop_loot(self, lot, owner):
		object_id = self._v_server.new_spawned_id()
		self._v_server.dropped_loot.setdefault(owner.object_id, {})[object_id] = lot
		self._v_server.send_game_message(owner.drop_client_loot, use_position=True, spawn_position=self.position, final_position=Vector3(self.position.x+(random.random()-0.5)*20, self.position.y, self.position.z+(random.random()-0.5)*20), currency=0, item_template=lot, loot_id=object_id, owner=owner.object_id, source_obj=self.object_id, address=owner.address)


	def request_die(self, address, unknown_bool:c_bit=None, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_int=0, killer_id:c_int64=None, loot_owner_id:c_int64=None):
		if self.armor != 0:
			self.armor = 0
		if self.life != 0:
			self.life = 0
		if self.imagination != 0:
			self.imagination = 0

		self._v_server.send_game_message(self.die, False, True, death_type, direction_relative_angle_xz, direction_relative_angle_y, direction_relative_force, kill_type, killer_id, loot_owner_id, broadcast=True)

		killer = self._v_server.get_object(killer_id)
		if killer and killer.lot == 1:
			# update missions that have the death of this lot as requirement
			for mission in killer.missions:
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.KillEnemy and self.lot in task.target:
							mission.increment_task(task, self._v_server, killer)

			# drops

			if self.currency_min is not None and self.currency_max is not None:
				currency = self.random_currency_amount()
				self._v_server.send_game_message(killer.drop_client_loot, currency=currency, item_template=-1, loot_id=0, owner=killer.object_id, source_obj=self.object_id, address=killer.address)

			if self.loot_matrix is not None:
				loot = self.random_loot()
				for lot in loot:
					self.drop_loot(lot, killer)

		if not isinstance(self, Comp108Component) and self.lot != 1:
			self._v_server.destruct(self)

	def resurrect(self, address, resurrect_immediately=False):
		pass
