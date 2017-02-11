from ..bitstream import c_bit, c_float, c_int, c_int64
from ..messages import broadcast
from .component import Component
from .mission import TaskType

class DestructibleComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.comp_id = comp_id
		self.object.destructible = self

	def init(self):
		comp = self.object._v_server.db.destructible_component[self.comp_id]
		self.object.stats.faction = comp[0]
		self.death_rewards = comp[1]
		self.object.stats._max_life = comp[2]
		self.object.stats._max_armor = comp[3]
		self.object.stats._max_imagination = comp[4]
		self.object.stats.life = self.object.stats.max_life
		self.object.stats.armor = self.object.stats.max_armor
		self.object.stats.imagination = self.object.stats.max_imagination
		self.object.stats.is_smashable = comp[5]
		del self.comp_id

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

	def deal_damage(self, damage, dealer):
		self.object.stats.armor = max(0, self.object.stats.armor - damage)
		if self.object.stats.armor - damage < 0:
			self.object.stats.life += self.object.stats.armor - damage
		self.object.handle("on_hit", dealer, silent=True)
		if self.object.stats.life <= 0:
			self.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=dealer.object_id, loot_owner_id=dealer.object_id)

	def request_die(self, unknown_bool:c_bit=None, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_int=0, killer_id:c_int64=None, loot_owner_id:c_int64=None):
		if self.object.stats.armor != 0:
			self.object.stats.armor = 0
		if self.object.stats.life != 0:
			self.object.stats.life = 0
		if self.object.stats.imagination != 0:
			self.object.stats.imagination = 0

		self.object.send_game_message("die", False, True, death_type, direction_relative_angle_xz, direction_relative_angle_y, direction_relative_force, kill_type, killer_id, loot_owner_id)

		killer = self.object._v_server.get_object(killer_id)
		if killer and hasattr(killer, "char"):
			killer.char.update_mission_task(TaskType.KillEnemy, self.object.lot)
			self.object.physics.drop_rewards(*self.death_rewards, killer)

		if hasattr(self.object, "char"):
			if self.object.char.vehicle_id != 0:
				self.object._v_server.game_objects[self.object.char.vehicle_id].comp_108.driver_id = 0
				self.object.char.vehicle_id = 0

			if self.object._v_server.world_control_object is not None and hasattr(self.object._v_server.world_control_object.script, "player_died"):
				self.object._v_server.world_control_object.script.player_died(player=self.object)
		else:
			if not hasattr(self.object, "comp_108"):
				self.object._v_server.destruct(self.object)

	@broadcast
	def resurrect(self, resurrect_immediately=False):
		pass
