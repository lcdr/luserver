from typing import Dict, List, Union

from bitstream import c_double, c_ubyte, ReadStream, Serializable, WriteStream

UNDEFINED_MARKER = 0
FALSE_MARKER = 2
TRUE_MARKER = 3
DOUBLE_MARKER = 5
STRING_MARKER = 6
ARRAY_MARKER = 9

_AMF3Type = Union[None, bool, float, str, dict]

class _AMF3Reader:
	def __init__(self, data: ReadStream):
		self.str_ref_table: List[str] = []
		self.data = data

	def read(self) -> _AMF3Type:
		return self.read_type()

	def read_u29(self) -> int:
		# variable-length unsigned integer
		value = 0
		for i in range(4):
			byte = self.data.read(c_ubyte)
			if i < 3:
				value = (value << 7) | (byte & 0x7f)
				if not byte & 0x80:
					break
			else:
				value = (value << 8) | byte
		return value

	def read_type(self) -> _AMF3Type:
		marker = self.data.read(c_ubyte)
		if marker == UNDEFINED_MARKER:
			return None
		if marker == FALSE_MARKER:
			return False
		if marker == TRUE_MARKER:
			return True
		if marker == DOUBLE_MARKER:
			return self.data.read(c_double)
		if marker == STRING_MARKER:
			return self.read_str()
		if marker == ARRAY_MARKER:
			return self.read_array()
		raise NotImplementedError(marker)

	def read_str(self) -> str:
		value = self.read_u29()
		is_literal = value & 0x01
		value >>= 1
		if not is_literal:
			return self.str_ref_table[value]
		str_ = self.data.read(bytes, length=value).decode()
		if str_:
			self.str_ref_table.append(str_)
		return str_

	def read_array(self) -> Dict[Union[str, int], _AMF3Type]:
		value = self.read_u29()
		is_literal = value & 0x01
		value >>= 1
		if not is_literal:
			raise NotImplementedError
		size = value
		array: Dict[Union[str, int], _AMF3Type] = {}
		while True:
			key = self.read_str()
			if key == "":
				break
			val = self.read_type()
			array[key] = val

		for i in range(size):
			val = self.read_type()
			array[i] = val

		return array

class _AMF3Writer:
	def __init__(self, out: WriteStream):
		self.out = out

	def write(self, data: dict) -> None:
		# todo: references (optional)
		self.write_type(data)

	def write_u29(self, value: int) -> None:
		if value > 0x1fffffff:
			raise ValueError("%i too large for u29" % value)
		if value < 0:
			raise ValueError("%i is not unsigned" % value)
		for i in range(4):
			if i < 3:
				byte = value & 0x7f
				bit = value > 0x7f
				self.out.write(c_ubyte((bit << 7) | byte))
				value >>= 7
				if not bit:
					break
			else:
				self.out.write(c_ubyte(value))

	def write_type(self, value: _AMF3Type) -> None:
		if value is None:
			self.out.write(c_ubyte(UNDEFINED_MARKER))
		elif value is False:
			self.out.write(c_ubyte(FALSE_MARKER))
		elif value is True:
			self.out.write(c_ubyte(TRUE_MARKER))
		elif isinstance(value, float):
			self.out.write(c_ubyte(DOUBLE_MARKER))
			self.out.write(c_double(value))
		elif isinstance(value, str):
			self.out.write(c_ubyte(STRING_MARKER))
			self.write_str(value)
		elif isinstance(value, dict):
			self.out.write(c_ubyte(ARRAY_MARKER))
			self.write_array(value)
		else:
			raise NotImplementedError(value)

	def write_str(self, str_: str) -> None:
		encoded = str_.encode()
		self.write_u29((len(encoded) << 1) | 0x01)
		self.out.write(encoded)

	def write_array(self, array: Dict[str, _AMF3Type]) -> None:
		self.write_u29(0x01) # literal, 0 dense items
		for key, value in array.items():
			assert isinstance(key, str)
			self.write_str(key)
			self.write_type(value)
		self.write_str("")

class AMF3(Serializable):
	def __init__(self, data: _AMF3Type):
		self.data = data

	def __str__(self) -> str:
		return str(self.data)

	def serialize(self, stream: WriteStream) -> None:
		writer = _AMF3Writer(stream)
		writer.write(self.data)

	@staticmethod
	def deserialize(stream: ReadStream) -> _AMF3Type:
		reader = _AMF3Reader(stream)
		return reader.read()
