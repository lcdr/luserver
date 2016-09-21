from .bitstream import BitStream, c_bool, c_float, c_int, c_int64, c_ubyte, c_uint

DATA_TYPE = {}
DATA_TYPE[str] = 0
DATA_TYPE[c_int] = 1
DATA_TYPE[c_float] = 3
DATA_TYPE[c_bool] = 7
DATA_TYPE[c_int64] = 9 # or 8?
DATA_TYPE[bytes] = 13 # let's just use bytes for 13
DATA_TYPE[0] = str
DATA_TYPE[1] = int # signed int
DATA_TYPE[3] = float
DATA_TYPE[5] = int # unsigned int
DATA_TYPE[7] = lambda x: bool(int(x))
DATA_TYPE[9] = int
DATA_TYPE[13] = lambda x: x.encode() # see above

def _value_to_ldf_text(type_, value):
	if isinstance(value, (list, tuple)):
		str_value = "+".join(_value_to_ldf_text(typ, val) for typ, val in value)
		value = ""
	else:
		str_value = str(value)
	return "%i:%s" % (DATA_TYPE[type_], str_value)

def to_ldf(obj, ldf_type):
	if ldf_type == "text":
		if isinstance(obj, dict):
			if len(obj) > 1:
				raise NotImplementedError
			output = "".join("%s=%s" % (key, _value_to_ldf_text(*value)) for key, value in obj.items())
		else:
			output = _value_to_ldf_text(*obj)

	elif ldf_type == "binary":
		if not isinstance(obj, dict):
			raise NotImplementedError
		output = BitStream()
		output.write(c_uint(len(obj)))
		for key, value in obj.items():
			value_type, value_value = value # meh this isn't exactly descriptive

			# can't use normal variable string writing because this writes the length of the encoded instead of the original (include option for this behavior?)
			encoded_key = key.encode("utf-16-le")
			output.write(c_ubyte(len(encoded_key)))
			output.write(encoded_key)
			output.write(c_ubyte(DATA_TYPE[value_type]))
			if value_type == str:
				output.write(value_value, length_type=c_uint)

			else:
				if value_type == bytes:
					output.write(c_uint(len(value_value)))
				output.write(value_type(value_value))

	return output

def from_ldf_type_value(type_value): # in its own function for use in luz path spawners where the structure is different
	data_type_id, value = type_value.split(":", maxsplit=1)
	data_type_id = int(data_type_id)
	return DATA_TYPE[data_type_id](value)

def from_ldf(ldf):
	ldf_dict = {}
	if isinstance(ldf, str):
		items = ldf.split("\x0a")
		for item in items:
			key, type_value = item.split("=", maxsplit=1)
			value = from_ldf_type_value(type_value)
			ldf_dict[key] = value
	elif isinstance(ldf, BitStream):
		for _ in range(ldf.read(c_uint)):
			encoded_key = ldf.read(bytes, length=ldf.read(c_ubyte))
			key = encoded_key.decode("utf-16-le")
			data_type_id = ldf.read(c_ubyte)
			if data_type_id == 0:
				value = ldf.read(str, length_type=c_uint)
			elif data_type_id == 1:
				value = ldf.read(c_int)
			elif data_type_id == 5:
				value = ldf.read(c_uint)
			elif data_type_id == 7:
				value = ldf.read(c_bool)
			elif data_type_id in (8, 9):
				value = ldf.read(c_int64)
			elif data_type_id == 13:
				value = ldf.read(bytes, length=ldf.read(c_uint))
			else:
				raise NotImplementedError(key, data_type_id)
			ldf_dict[key] = value
	else:
		raise NotImplementedError

	return ldf_dict
