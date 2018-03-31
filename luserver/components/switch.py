from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import Config, GameObject, Player
from .component import Component

DEACTIVATE_INTERVAL = 5

class SwitchComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self._flags["_activated"] = "placeholder_flag" # needed to register changes for serialization
		self._enabled = True
		self._activated = False

	@property
	def activated(self) -> bool:
		return self._activated

	@activated.setter
	def activated(self, value: bool) -> None:
		if not self._enabled:
			return
		self._activated = value
		if value:
			self.object.handle("switch_activated")
		else:
			self.object.handle("switch_deactivated")

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(self.activated))

	def on_rebuild_init(self) -> None:
		self._enabled = False

	def on_complete_rebuild(self, player: Player) -> None:
		self._enabled = True

	def on_enter(self, player: Player) -> None:
		self.activated = True
		self.object.call_later(DEACTIVATE_INTERVAL, self.deactivate)

	def deactivate(self) -> None:
		self.activated = False
