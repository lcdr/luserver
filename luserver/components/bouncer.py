from ..bitstream import c_bit

class BouncerComponent:
	def __init__(self, comp_id):
		pass

	def serialize(self, out, is_creation):
		out.write(c_bit(False))
