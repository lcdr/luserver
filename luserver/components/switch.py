import asyncio

from ..bitstream import c_bit
from .component import Component

DEACTIVATE_INTERVAL = 5

class SwitchComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_activated"] = "placeholder_flag" # needed to register changes for serialization
		self._activated = False

	@property
	def activated(self):
		return self._activated

	@activated.setter
	def activated(self, value):
		self._activated = value
		if hasattr(self.object, "trigger"):
			if value:
				if hasattr(self.object.trigger, "on_activated"):
					self.object.trigger.on_activated()
			else:
				if hasattr(self.object.trigger, "on_deactivated"):
					self.object.trigger.on_deactivated()

	def serialize(self, out, is_creation):
		out.write(c_bit(self.activated))

	def on_enter(self, player):
		self.activated = True
		asyncio.get_event_loop().call_later(DEACTIVATE_INTERVAL, self.deactivate)

	def deactivate(self):
		self.activated = False
