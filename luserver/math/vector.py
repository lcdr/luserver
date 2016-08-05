import math

class Vector3:
	def update(self, x=0, y=0, z=0):
		if isinstance(x, Vector3):
			self.x = x.x
			self.y = x.y
			self.z = x.z
		else:
			self.x = x
			self.y = y
			self.z = z

	__init__ = update

	def __repr__(self):
		return "Vector3(%g, %g, %g)" % (self.x, self.y, self.z)

	def __eq__(self, other):
		if isinstance(other, Vector3):
			return other.x == self.x and other.y == self.y and other.z == self.z
		return NotImplemented

	def __add__(self, other):
		return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

	def __sub__(self, other):
		return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

	def __mul__(self, other):
		return Vector3(self.x * other, self.y * other, self.z * other)

	__rmul__ = __mul__

	def magnitude(self):
		return math.sqrt(self.sq_magnitude())

	def sq_magnitude(self):
		return self.x**2 + self.y**2 + self.z**2

	def unit(self):
		mag = self.magnitude()
		if mag == 0:
			return Vector3(0, 0, 0) # seems like the most reasonable thing to do
		return Vector3(self.x/mag, self.y/mag, self.z/mag)

	def cross(self, other):
		return Vector3(self.y*other.z - self.z*other.y, self.z*other.x - self.x*other.z, self.x*other.y - self.y*other.x)

	def dot(self, other):
		return self.x*other.x + self.y*other.y + self.z*other.z

	def sq_distance(self, other):
		diff = self - other
		return diff.sq_magnitude()

	def rotate(self, quaternion):
		quatvector = Vector3(quaternion.x, quaternion.y, quaternion.z)
		scalar = quaternion.w

		return 2 * quatvector.dot(self) * quatvector + (scalar*scalar - quatvector.dot(quatvector)) * self + 2 * scalar * quatvector.cross(self)

Vector3.zero = Vector3(0, 0, 0)
Vector3.right = Vector3(1, 0, 0)
Vector3.left = Vector3(-1, 0, 0)
Vector3.up = Vector3(0, 1, 0)
Vector3.down = Vector3(0, -1, 0)
Vector3.forward = Vector3(0, 0, 1)
Vector3.back = Vector3(0, 0, -1)
Vector3.one = Vector3(1, 1, 1)
