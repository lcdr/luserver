from ..bitstream import c_bit
from ..math.quaternion import Quaternion

class BaseCombatAIComponent:
	def __init__(self, comp_id):
		self.targeted_player = None

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def update(self): # currently disabled
		if self.targeted_player is None:
			players = [obj for obj in self._v_server.game_objects.values() if obj.lot == 1]
			nearest_dist = 10 # starting distance is maximum distance
			for player in players:
				dist = self.position.sq_distance(player.position)
				if dist < nearest_dist:
					self.targeted_player = player
					nearest_dist = dist
			if self.targeted_player is None:
				# no player within range
				return

		self.velocity.update((self.targeted_player.position - self.position).unit() * 1.2)
		self.attr_changed("velocity")
		self.position += self.velocity
		self.attr_changed("position")
		pos_diff = self.targeted_player.position - self.position
		pos_diff.y = 0
		#self.angular_velocity = self.targeted_player.angular_velocity
		self.rotation.update(self.targeted_player.rotation)
		self.attr_changed("rotation")
		#self.rotation = Quaternion.look_rotation(pos_diff)
