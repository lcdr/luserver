import random

from ..bitstream import c_bit, c_int
from ..modules.chat import ALL_MODELS
from .component import Component

CYCLE_INTERVAL = 10

class ExhibitComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["exhibited_lot"] = "exhibit_flag"
		self.random_exhibit()

	def random_exhibit(self):
		self.exhibited_lot = random.choice(ALL_MODELS)
		self.object.call_later(CYCLE_INTERVAL, self.random_exhibit)

	def serialize(self, out, is_creation):
		out.write(c_bit(self.exhibit_flag or is_creation))
		if self.exhibit_flag or is_creation:
			out.write(c_int(self.exhibited_lot))
			self.exhibit_flag = False
