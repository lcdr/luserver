from pyraknet.bitstream import c_bit
from .component import Component

DEACTIVATE_INTERVAL = 5

class SwitchComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_activated"] = "placeholder_flag" # needed to register changes for serialization
		self._enabled = True
		self._activated = False
		self.object.add_handler("rebuild_init", self._on_rebuild_init)
		self.object.add_handler("complete_rebuild", self._on_rebuild_complete)

	@property
	def activated(self):
		return self._activated

	@activated.setter
	def activated(self, value):
		if not self._enabled:
			return
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

	def _on_rebuild_init(self, _obj):
		self._enabled = False

	def _on_rebuild_complete(self, _obj, player):
		self._enabled = True

	def on_enter(self, player):
		self.activated = True
		self.object.call_later(DEACTIVATE_INTERVAL, self.deactivate)

	def deactivate(self):
		self.activated = False
