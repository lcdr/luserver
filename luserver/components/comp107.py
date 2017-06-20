from ..bitstream import c_bit
from .component import Component

class Comp107Component(Component):
	def serialize(self, out, is_creation):
		out.write(c_bit(False))
