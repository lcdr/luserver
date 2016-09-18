from ..bitstream import c_bit
from ..math.quaternion import Quaternion
from .component import Component

class BaseCombatAIComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.targeted_player = None

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def update(self): # currently disabled
		if self.targeted_player is None:
			players = [obj for obj in self.object._v_server.game_objects.values() if obj.lot == 1]
			nearest_dist = 10 # starting distance is maximum distance
			for player in players:
				dist = self.object.physics.position.sq_distance(player.physics.position)
				if dist < nearest_dist:
					self.targeted_player = player
					nearest_dist = dist
			if self.targeted_player is None:
				# no player within range
				return

		self.object.physics.velocity.update((self.targeted_player.physics.position - self.object.physics.position).unit() * 1.2)
		self.object.physics.attr_changed("velocity")
		self.object.physics.position += self.object.physics.velocity
		self.object.physics.attr_changed("position")
		pos_diff = self.targeted_player.physics.position - self.object.physics.position
		pos_diff.y = 0
		#self.angular_velocity = self.targeted_player.physics.angular_velocity
		self.object.physics.rotation.update(self.targeted_player.physics.rotation)
		self.object.physics.attr_changed("rotation")
		#self.object.physics.rotation = Quaternion.look_rotation(pos_diff)
