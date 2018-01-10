import enum
import numbers

from pyraknet.bitstream import c_bool, c_double, c_float, c_int, c_int64, c_ubyte, c_uint, ReadStream, WriteStream

class LDFDataType(enum.Enum):
	STRING = 0
	INT32 = 1
	FLOAT = 3
	DOUBLE = 4
	UINT32 = 5
	BOOLEAN = 7
	INT64_8 = 8
	INT64_9 = 9
	BYTES = 13

class LDF(dict):
	def __init__(self, source=None):
		super().__init__()
		if source is not None:
			if isinstance(source, str):
				self.from_str(source)
			elif isinstance(source, ReadStream):
				self.from_bitstream(source)

	def __getitem__(self, key):
		return self.ldf_get(key)[1]

	def __setitem__(self, key, value):
		return self.ldf_set(key, self.ldf_get(key)[0], value)

	def ldf_get(self, key):
		return super().__getitem__(key)

	def ldf_set(self, key, data_type, value):
		if not isinstance(data_type, LDFDataType):
			raise TypeError
		if data_type == LDFDataType.STRING:
			if not isinstance(value, (str, list, tuple)):
				raise TypeError
		elif data_type in (LDFDataType.INT32, LDFDataType.UINT32, LDFDataType.INT64_8, LDFDataType.INT64_9):
			if not isinstance(value, int):
				raise TypeError
			if data_type == LDFDataType.UINT32:
				if value < 0:
					raise ValueError
		elif data_type in (LDFDataType.FLOAT, LDFDataType.DOUBLE):
			if not isinstance(value, numbers.Real):
				raise TypeError
		elif data_type == LDFDataType.BOOLEAN:
			if not isinstance(value, bool):
				raise TypeError
		elif data_type == LDFDataType.BYTES:
			if not isinstance(value, bytes):
				raise TypeError
		return super().__setitem__(key, (data_type, value))

	def from_str(self, source):
		items = source.split("\x0a")
		for item in items:
			key, type_value = item.split("=", maxsplit=1)
			data_type, value = self.from_str_type(type_value)
			self.ldf_set(key, data_type, value)

	def to_str(self):
		return "\n".join("%s=%s" % (key, self.to_str_type(*value)) for key, value in super().items())

	@staticmethod
	def from_str_type(type_value):
		data_type_id, value = type_value.split(":", maxsplit=1)
		data_type = LDFDataType(int(data_type_id))
		if data_type == LDFDataType.STRING:
			value = value
		elif data_type in (LDFDataType.INT32, LDFDataType.UINT32, LDFDataType.INT64_8, LDFDataType.INT64_9):
			value = int(value)
		elif data_type in (LDFDataType.FLOAT, LDFDataType.DOUBLE):
			value = float(value)
		elif data_type == LDFDataType.BOOLEAN:
			value = bool(int(value))
		elif data_type == LDFDataType.BYTES:
			value = value.encode()
		return data_type, value

	@staticmethod
	def to_str_type(data_type, value):
		if isinstance(value, (list, tuple)):
			str_value = "+".join(LDF.to_str_type(data_type, val) for data_type, val in value)
		else:
			if data_type == LDFDataType.STRING:
				str_value = value
			elif data_type in (LDFDataType.INT32, LDFDataType.FLOAT, LDFDataType.DOUBLE, LDFDataType.UINT32, LDFDataType.INT64_8, LDFDataType.INT64_9):
				str_value = str(value)
			elif data_type == LDFDataType.BOOLEAN:
				str_value = str(int(value))
			elif data_type == LDFDataType.BYTES:
				str_value = value.decode()
		return "%i:%s" % (data_type.value, str_value)

	def from_bitstream(self, source):
		for _ in range(source.read(c_uint)):
			encoded_key = source.read(bytes, length=source.read(c_ubyte))
			key = encoded_key.decode("utf-16-le")
			data_type = LDFDataType(source.read(c_ubyte))
			if data_type == LDFDataType.STRING:
				value = source.read(str, length_type=c_uint)
			elif data_type == LDFDataType.INT32:
				value = source.read(c_int)
			elif data_type == LDFDataType.FLOAT:
				value = source.read(c_float)
			elif data_type == LDFDataType.DOUBLE:
				raise NotImplementedError(data_type)
			elif data_type == LDFDataType.UINT32:
				value = source.read(c_uint)
			elif data_type == LDFDataType.BOOLEAN:
				value = source.read(c_bool)
			elif data_type in (LDFDataType.INT64_8, LDFDataType.INT64_9):
				value = source.read(c_int64)
			elif data_type == LDFDataType.BYTES:
				value = source.read(bytes, length=source.read(c_uint))
			self.ldf_set(key, data_type, value)

	def to_bitstream(self):
		uncompressed = WriteStream()
		uncompressed.write(c_uint(len(self)))
		for key, value in super().items():
			data_type, value = value
			# can't use normal variable string writing because this writes the length of the encoded instead of the original (include option for this behavior?)
			encoded_key = key.encode("utf-16-le")
			uncompressed.write(c_ubyte(len(encoded_key)))
			uncompressed.write(encoded_key)
			uncompressed.write(c_ubyte(data_type.value))
			if data_type == LDFDataType.STRING:
				uncompressed.write(value, length_type=c_uint)
			elif data_type == LDFDataType.INT32:
				uncompressed.write(c_int(value))
			elif data_type == LDFDataType.FLOAT:
				uncompressed.write(c_float(value))
			elif data_type == LDFDataType.DOUBLE:
				uncompressed.write(c_double(value))
			elif data_type == LDFDataType.UINT32:
				uncompressed.write(c_uint(value))
			elif data_type == LDFDataType.BOOLEAN:
				uncompressed.write(c_bool(value))
			elif data_type in (LDFDataType.INT64_8, LDFDataType.INT64_9):
				uncompressed.write(c_int64(value))
			elif data_type == LDFDataType.BYTES:
				uncompressed.write(c_uint(len(value)))
				uncompressed.write(value)

		uncompressed = bytes(uncompressed)

		output = WriteStream()
		is_compressed = False
		if not is_compressed:
			output.write(c_uint(len(uncompressed)+1))
		else:
			raise NotImplementedError
		output.write(c_bool(is_compressed))
		output.write(uncompressed)
		return output
