from ..bitstream import c_bit
from ..math.quaternion import Quaternion
from .component import Component

UPDATE_INTERVAL = 1 # todo: make interval skill-dependent

class BaseCombatAIComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.ai = self
		self._flags["target"] = "ai_flag"
		self.target = None
		self.update_handle = None

	def on_startup(self):
		self.enable()

	def enable(self):
		if not hasattr(self.object, "stats"):
			return
		self.update_handle = self.object.call_later(UPDATE_INTERVAL, self.update)

	def disable(self):
		if self.update_handle is not None:
			self.object.cancel_callback(self.update_handle)

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def update(self):
		# todo: move some targeting logic to TacArc
		self.target = None
		enemy_factions = self.object._v_server.db.factions.get(self.object.stats.faction, ())
		# todo: make distance skill-dependent
		nearest_dist = 7**2 # starting distance is maximum distance
		for obj in self.object._v_server.game_objects.values():
			if hasattr(obj, "stats") and obj.stats.faction in enemy_factions:
				dist = self.object.physics.position.sq_distance(obj.physics.position)
				if dist < nearest_dist:
					self.target = obj
					nearest_dist = dist
		if self.target is not None:
			#self.object.physics.velocity.update((self.target.physics.position - self.object.physics.position).unit() * 1.2)
			#self.object.physics.attr_changed("velocity")
			#self.object.physics.position += self.object.physics.velocity
			#self.object.physics.attr_changed("position")
			pos_diff = self.target.physics.position - self.object.physics.position
			pos_diff.y = 0
			#self.object.physics.angular_velocity = self.target.physics.angular_velocity
			#self.object.physics.rotation.update(self.target.physics.rotation)
			self.object.physics.attr_changed("rotation")
			self.object.physics.rotation = Quaternion.look_rotation(pos_diff)
			for skill_id in self.object.skill.skills:
				self.object.skill.cast_skill(skill_id, self.target)

		self.update_handle = self.object.call_later(UPDATE_INTERVAL, self.update)
