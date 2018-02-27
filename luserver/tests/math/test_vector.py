import unittest
from luserver.math.vector import Vector3

class Vector3Test(unittest.TestCase):
	vec1 = Vector3(1, 2, 3)
	vec2 = Vector3(4, 5, 6)

	def test_init(self):
		self.assertEqual(Vector3(), Vector3.zero)
		self.assertEqual(Vector3(0, 0, 1), Vector3.forward)
		self.assertEqual(Vector3(Vector3.forward), Vector3.forward)

	def test_equal(self):
		self.assertEqual(self.vec1, self.vec1)

	def test_negate(self):
		self.assertEqual(-self.vec1, Vector3(-1, -2, -3))

	def test_add(self):
		self.assertEqual(self.vec1 + self.vec2, Vector3(5, 7, 9))

	def test_sub(self):
		self.assertEqual(self.vec1 - self.vec2, Vector3(-3, -3, -3))

	def test_mul_scalar(self):
		self.assertEqual(self.vec1 * 10, Vector3(10, 20, 30))

	def test_mul_vector(self):
		with self.assertRaises(TypeError):
			self.vec1 * self.vec2

	def test_truediv(self):
		self.assertEqual(self.vec1 / 10, Vector3(0.1, 0.2, 0.3))

	def test_magnitude(self):
		self.assertEqual(Vector3(0, 3, 4).magnitude(), 5)

	def test_sq_magnitude(self):
		self.assertEqual(Vector3(0, 3, 4).sq_magnitude(), 25)

	def test_unit(self):
		self.assertEqual(Vector3(0, 0, 10).unit(), Vector3(0, 0, 1))

	def test_cross(self):
		self.assertEqual(self.vec1.cross(self.vec2), Vector3(-3, 6, -3))

	def test_dot(self):
		self.assertEqual(self.vec1.dot(self.vec2), 32)

	def test_hadamard(self):
		self.assertEqual(self.vec1.hadamard(self.vec2), Vector3(4, 10, 18))

	def test_sq_distance(self):
		self.assertEqual(self.vec1.sq_distance(self.vec2), 27)

	def test_distance(self):
		self.assertEqual(self.vec1.distance(Vector3(1, 6, 6)), 5)
