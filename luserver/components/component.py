from abc import ABC, abstractmethod

from bitstream import WriteStream
from ..game_object import Config, FlagObject, GameObject

class Component(FlagObject, ABC):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__()
		self.object = obj
		for name in dir(self):
			if name.startswith("on_"):
				self.object.add_handler(name[3:], getattr(self, name))

	def attr_changed(self, name: str) -> None:
		if hasattr(self, "_flags") and name in self._flags:
			setattr(self, self._flags[name], hasattr(self, name))
			self.object.signal_serialize()

	@abstractmethod
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass
