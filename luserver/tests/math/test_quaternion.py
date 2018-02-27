import math
import unittest

from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3

class QuaternionTest(unittest.TestCase):
	quat1 = Quaternion.identity

	def test_init(self):
		self.assertEqual(Quaternion(), Quaternion.identity)
		self.assertEqual(Quaternion(0, 0, 0, 1), Quaternion.identity)
		self.assertEqual(Quaternion(Quaternion.identity), Quaternion.identity)

	def test_equal(self):
		self.assertEqual(self.quat1, self.quat1)

	def test_look_rotation(self):
		self.assertEqual(Quaternion.look_rotation(Vector3(0, 0, 10)), Quaternion.identity)

	def test_angle_axis(self):
		result = Quaternion.angle_axis(4*math.pi, Vector3.up)
		self.assertAlmostEqual(result.x, Quaternion.identity.x)
		self.assertAlmostEqual(result.y, Quaternion.identity.y)
		self.assertAlmostEqual(result.z, Quaternion.identity.z)
		self.assertAlmostEqual(result.w, Quaternion.identity.w)

	def test_rotate(self):
		self.assertEqual(Quaternion(0, 1, 0, 0).rotate(Vector3(1, 2, 3)), Vector3(-1, 2, -3))
