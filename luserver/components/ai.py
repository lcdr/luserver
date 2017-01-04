import asyncio

from ..bitstream import c_bit
from ..math.quaternion import Quaternion
from .component import Component

UPDATE_INTERVAL = 1

class BaseCombatAIComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.ai = self
		self._flags["target"] = "ai_flag"
		self.target = None

	def enable(self):
		asyncio.get_event_loop().call_later(UPDATE_INTERVAL, self.update)

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def update(self):
		players = [obj for obj in self.object._v_server.game_objects.values() if hasattr(obj, "char")]
		nearest_dist = 100 # starting distance is maximum distance
		for player in players:
			dist = self.object.physics.position.sq_distance(player.physics.position)
			if dist < nearest_dist:
				self.target = player
				print("targeting", player)
				nearest_dist = dist
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

		asyncio.get_event_loop().call_later(UPDATE_INTERVAL, self.update)
