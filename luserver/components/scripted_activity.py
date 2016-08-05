from ..bitstream import c_bit, c_float, c_int64, c_uint

class ScriptedActivityComponent:
	def __init__(self, comp_id):
		self._flags["players"] = "activity_flag"
		self.players = []

	def serialize(self, out, is_creation):
		out.write(c_bit(self.activity_flag))
		if self.activity_flag:
			out.write(c_uint(len(self.players)))
			for object_id in self.players:
				out.write(c_int64(object_id))
				for _ in range(10):
					out.write(c_float(0))
			self.activity_flag = False
