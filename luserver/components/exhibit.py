import random

from bitstream import c_int, WriteStream
from ..game_object import Config, GameObject
from .component import Component

_CYCLE_INTERVAL = 10

class ExhibitComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_exhibited_lot"] = "_exhibit_flag"
		self._random_exhibit()

	def _random_exhibit(self) -> None:
		self._exhibited_lot = random.choice([4009]) # todo: add a nice list of objects to display here
		self.object.call_later(_CYCLE_INTERVAL, self._random_exhibit)

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("_exhibit_flag", out, is_creation):
			out.write(c_int(self._exhibited_lot))
