from typing import Dict

from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import GameObject, Player
from .component import Component

DEACTIVATE_INTERVAL = 5

class SwitchComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Dict[str, object], comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_activated"] = "placeholder_flag" # needed to register changes for serialization
		self._enabled = True
		self._activated = False
		self.object.add_handler("rebuild_init", self._on_rebuild_init)
		self.object.add_handler("complete_rebuild", self._on_rebuild_complete)

	@property
	def activated(self) -> bool:
		return self._activated

	@activated.setter
	def activated(self, value: bool) -> None:
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

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(self.activated))

	def _on_rebuild_init(self, _obj: GameObject) -> None:
		self._enabled = False

	def _on_rebuild_complete(self, _obj: GameObject, player: Player) -> None:
		self._enabled = True

	def on_enter(self, player: Player) -> None:
		self.activated = True
		self.object.call_later(DEACTIVATE_INTERVAL, self.deactivate)

	def deactivate(self) -> None:
		self.activated = False
