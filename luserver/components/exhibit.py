import random

from pyraknet.bitstream import c_bit, c_int
from .component import Component

_CYCLE_INTERVAL = 10

class ExhibitComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_exhibited_lot"] = "_exhibit_flag"
		self._random_exhibit()

	def _random_exhibit(self):
		self._exhibited_lot = random.choice([4009]) # todo: add a nice list of objects to display here
		self.object.call_later(_CYCLE_INTERVAL, self._random_exhibit)

	def serialize(self, out, is_creation):
		out.write(c_bit(self._exhibit_flag or is_creation))
		if self._exhibit_flag or is_creation:
			out.write(c_int(self._exhibited_lot))
			self._exhibit_flag = False
