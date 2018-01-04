from pyraknet.bitstream import c_bit
from .component import Component

class BouncerComponent(Component):
	def serialize(self, out, is_creation):
		out.write(c_bit(False))
