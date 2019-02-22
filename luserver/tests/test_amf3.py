import unittest
from functools import partial

from luserver.amf3 import AMF3, _AMF3Reader, _AMF3Writer
from bitstream import ReadStream, WriteStream

class AMF3Test(unittest.TestCase):
	encodes = {
		None: b"\x00",
		False: b"\x02",
		True: b"\x03",
		0.42: b"\x05\xe1z\x14\xaeG\xe1\xda?",
		"test": b"\x06\x09test"
	}

	def do_test(self, original, encoded):
		with self.subTest(type="read", original=original, encoded=encoded):
			stream = ReadStream(encoded)
			self.assertEqual(stream.read(AMF3), original)
		with self.subTest(type="write", original=original, encoded=encoded):
			stream = WriteStream()
			stream.write(AMF3(original))
			self.assertEqual(bytes(stream), encoded)

	def test_amf3(self):
		for original, encoded in self.encodes.items():
			self.do_test(original, encoded)

	def test_array(self):
		original = {"undefined": None, "false": False, "true": True, "double": 0.42, "string": "test"}
		encoded = b"\t\x01\x13undefined\x00\x0bfalse\x02\ttrue\x03\rdouble\x05\xe1z\x14\xaeG\xe1\xda?\rstring\x06\ttest\x01"
		self.do_test(original, encoded)

	u29encodes = {
		0x7f: b"\x7f",
		0x3fff: b"\xff\x7f",
		0x1fffff: b"\xff\xff\x7f",
		0x1fffffff: b"\xff\xff\xff\xff"
	}

	def do_u29_test(self, original, encoded):
		with self.subTest(type="read", original=original, encoded=encoded):
			stream = ReadStream(encoded)
			self.assertEqual(_AMF3Reader(stream).read_u29(), original)
		with self.subTest(type="write", original=original, encoded=encoded):
			stream = WriteStream()
			writer = _AMF3Writer(stream)
			writer.write_u29(original)
			self.assertEqual(bytes(stream), encoded)

	def test_u29(self):
		for original, encoded in self.u29encodes.items():
			self.do_u29_test(original, encoded)
