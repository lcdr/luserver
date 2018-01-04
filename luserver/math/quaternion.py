import math
from numbers import Real
from typing import ClassVar

from pyraknet.bitstream import c_float, Serializable
from .vector import Vector3

class Quaternion(Serializable):
	identity: "ClassVar[Quaternion]"
	x: float
	y: float
	z: float
	w: float
	__slots__ = "x", "y", "z", "w"

	def __init__(self, x=None, y=None, z=None, w=None):
		if x is None:
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0
			self.w = 1.0
		elif isinstance(x, Quaternion):
			self.x = x.x
			self.y = x.y
			self.z = x.z
			self.w = x.w
		elif isinstance(x, Real) and isinstance(y, Real) and isinstance(z, Real) and isinstance(w, Real):
			self.x = float(x)
			self.y = float(y)
			self.z = float(z)
			self.w = float(w)
		else:
			raise TypeError

	update = __init__

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

	def serialize(self, stream):
		stream.write(c_float(self.x))
		stream.write(c_float(self.y))
		stream.write(c_float(self.z))
		stream.write(c_float(self.w))

	@staticmethod
	def deserialize(stream):
		return Quaternion(stream.read(c_float), stream.read(c_float), stream.read(c_float), stream.read(c_float))

Quaternion.identity = Quaternion(0, 0, 0, 1)
