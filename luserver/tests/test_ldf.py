import unittest
from luserver.ldf import LDF, LDFDataType

class LDFTest(unittest.TestCase):
	BYTES = b"\xb0\x00\x00\x00\x00\t\x00\x00\x00\x06s\x00t\x00r\x00\x00\x04\x00\x00\x00t\x00e\x00s\x00t\x00\ni\x00n\x00t\x003\x002\x00\x01\xd6\xff\xff\xff\nf\x00l\x00o\x00a\x00t\x00\x03\xc3\xf5H@\x0cd\x00o\x00u\x00b\x00l\x00e\x00\x04\x1f\x85\xebQ\xb8\x1e\t@\x0cu\x00i\x00n\x00t\x003\x002\x00\x05*\x00\x00\x00\x08b\x00o\x00o\x00l\x00\x07\x01\x0ei\x00n\x00t\x006\x004\x00_\x008\x00\x08\x00\x00\x00\x00\x00\x01\x00\x00\x0ei\x00n\x00t\x006\x004\x00_\x009\x00\x08\x00\x00\x00\x00\x00\x04\x00\x00\nb\x00y\x00t\x00e\x00s\x00\r\x04\x00\x00\x00test"

	def setUp(self):
		self.ldf = LDF()

	def test_get_missing(self):
		with self.assertRaises(KeyError):
			self.ldf.ldf_get("missing")
		with self.assertRaises(KeyError):
			self.ldf["missing"]

	def test_assign_missing(self):
		with self.assertRaises(KeyError):
			self.ldf["missing"] = "value"

	def test_set_get(self):
		values = [
			("str", LDFDataType.STRING, "test"),
			("int32", LDFDataType.INT32, -42),
			("float", LDFDataType.FLOAT, 3.14),
			("double", LDFDataType.DOUBLE, 3.14),
			("uint32", LDFDataType.UINT32, 42),
			("bool", LDFDataType.BOOLEAN, True),
			("int64_8", LDFDataType.INT64_8, 1 << 40),
			("int64_9", LDFDataType.INT64_8, 1 << 42),
			("bytes", LDFDataType.BYTES, b"test"),
		]

		for key, data_type, value in values:
			self.ldf.ldf_set(key, data_type, value)
		for key, data_type, value in values:
			self.assertEqual(self.ldf.ldf_get(key), (data_type, value))
			self.assertEqual(self.ldf[key], value)

	def test_contains(self):
		self.ldf.ldf_set("testkey", LDFDataType.STRING, "testvalue")
		self.assertTrue("testkey" in self.ldf)

	def test_not_contains(self):
		self.assertFalse("missing" in self.ldf)

	def test_bool(self):
		self.assertFalse(bool(self.ldf))
		self.ldf.ldf_set("testkey", LDFDataType.STRING, "testvalue")
		self.assertTrue(bool(self.ldf))

	def test_to_bytes(self):
		self.test_set_get()
		b = self.ldf.to_bytes()
		self.assertEqual(b, self.BYTES)
