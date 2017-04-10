import collections.abc
import math
from .vector import Vector3

class Quaternion:
	def update(self, x=0, y=0, z=0, w=1):
		if isinstance(x, Quaternion):
			self.x = x.x
			self.y = x.y
			self.z = x.z
			self.w = x.w
		elif isinstance(x, collections.abc.Sequence):
			if len(x) != 4:
				raise ValueError("Sequence must have length 4")
			self.x = x[0]
			self.y = x[1]
			self.z = x[2]
			self.w = x[3]
		else:
			self.x = x
			self.y = y
			self.z = z
			self.w = w

	__init__ = update

	def __repr__(self):
		return "Quaternion(%g, %g, %g, %g)" % (self.x, self.y, self.z, self.w)

	def __eq__(self, other):
		if isinstance(other, Quaternion):
			return other.x == self.x and other.y == self.y and other.z == self.z and other.w == self.w
		return NotImplemented

	@staticmethod
	def look_rotation(direction):
		direction = direction.unit()
		dot = -direction.dot(Vector3.back)
		if abs(dot - 1) < 0.000001:
			# vectors point in the same direction
			return Quaternion()
		if abs(dot + 1) < 0.000001:
			# vectors point in opposite directions
			return Quaternion(Vector3.up.x, Vector3.up.y, Vector3.up.z, math.pi)

		rot_angle = math.acos(dot)
		rot_axis = direction.cross(Vector3.back)
		return Quaternion.angle_axis(rot_angle, rot_axis)

	@staticmethod
	def angle_axis(angle, axis):
		axis = axis.unit()
		s = math.sin(angle / 2)
		return Quaternion(axis.x*s, axis.y*s, axis.z*s, math.cos(angle / 2))

Quaternion.identity = Quaternion(0, 0, 0, 1)
