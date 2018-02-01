from pyraknet.bitstream import c_bit, WriteStream
from .component import Component

class BouncerComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))
