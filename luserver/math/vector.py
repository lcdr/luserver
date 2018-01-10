import math
from numbers import Real
from typing import ClassVar, overload

from pyraknet.bitstream import c_float, ReadStream, Serializable, WriteStream

class Vector3(Serializable):
	zero: "ClassVar[Vector3]"
	right: "ClassVar[Vector3]"
	left: "ClassVar[Vector3]"
	up: "ClassVar[Vector3]"
	down: "ClassVar[Vector3]"
	forward: "ClassVar[Vector3]"
	back: "ClassVar[Vector3]"
	one: "ClassVar[Vector3]"
	x: float
	y: float
	z: float
	__slots__ = "x", "y", "z"

	@overload
	def __init__(self):
		pass

	@overload
	def __init__(self, x: Real, y: Real, z: Real):
		pass

	@overload
	def __init__(self, x: "Vector3"):
		pass

	def __init__(self, x=None, y=None, z=None):
		if x is None:
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0
		elif isinstance(x, Vector3):
			self.x = x.x
			self.y = x.y
			self.z = x.z
		elif isinstance(x, Real) and isinstance(y, Real) and isinstance(z, Real):
			self.x = float(x)
			self.y = float(y)
			self.z = float(z)
		else:
			raise TypeError

	update = __init__

	def __repr__(self):
		return "Vector3(%g, %g, %g)" % (self.x, self.y, self.z)

	def __neg__(self):
		return Vector3(-self.x, -self.y, -self.z)

	def __eq__(self, other):
		if not isinstance(other, Vector3):
			return NotImplemented
		return other.x == self.x and other.y == self.y and other.z == self.z

	def __add__(self, other):
		if not isinstance(other, Vector3):
			return NotImplemented
		return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

	def __sub__(self, other):
		if not isinstance(other, Vector3):
			return NotImplemented
		return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

	def __mul__(self, other):
		if isinstance(other, Vector3):
			raise TypeError("Multiple multiplications for vectors possible, choose one of cross, dot, hadamard")
		return Vector3(self.x * other, self.y * other, self.z * other)

	__rmul__ = __mul__

	def __truediv__(self, other):
		return Vector3(self.x / other, self.y / other, self.z / other)

	def magnitude(self) -> float:
		return math.sqrt(self.sq_magnitude())

	def sq_magnitude(self) -> float:
		return self.x**2 + self.y**2 + self.z**2

	def unit(self) -> "Vector3":
		mag = self.magnitude()
		if mag == 0:
			return Vector3(0, 0, 0) # seems like the most reasonable thing to do
		return Vector3(self.x/mag, self.y/mag, self.z/mag)

	def cross(self, other: "Vector3") -> "Vector3":
		return Vector3(self.y*other.z - self.z*other.y, self.z*other.x - self.x*other.z, self.x*other.y - self.y*other.x)

	def dot(self, other: "Vector3") -> float:
		return self.x*other.x + self.y*other.y + self.z*other.z

	def hadamard(self, other: "Vector3") -> "Vector3":
		return Vector3(self.x * other.x, self.y * other.y, self.z * other.z)

	def sq_distance(self, other: "Vector3") -> float:
		#diff = self - other
		#return diff.sq_magnitude()
		# optimized version without creating a new object
		dx = self.x - other.x
		dy = self.y - other.y
		dz = self.z - other.z
		return dx**2 + dy**2 + dz**2

	def distance(self, other: "Vector3") -> float:
		return math.sqrt(self.sq_distance(other))

	def rotated(self, quaternion) -> "Vector3":
		quatvector = Vector3(quaternion.x, quaternion.y, quaternion.z)
		scalar = quaternion.w

		return 2 * quatvector.dot(self) * quatvector + (scalar*scalar - quatvector.dot(quatvector)) * self + 2 * scalar * quatvector.cross(self)

	def serialize(self, stream: WriteStream) -> None:
		stream.write(c_float(self.x))
		stream.write(c_float(self.y))
		stream.write(c_float(self.z))

	@staticmethod
	def deserialize(stream: ReadStream) -> "Vector3":
		return Vector3(stream.read(c_float), stream.read(c_float), stream.read(c_float))

Vector3.zero = Vector3(0, 0, 0)
Vector3.right = Vector3(1, 0, 0)
Vector3.left = Vector3(-1, 0, 0)
Vector3.up = Vector3(0, 1, 0)
Vector3.down = Vector3(0, -1, 0)
Vector3.forward = Vector3(0, 0, 1)
Vector3.back = Vector3(0, 0, -1)
Vector3.one = Vector3(1, 1, 1)
