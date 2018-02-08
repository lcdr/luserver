from abc import ABC, abstractmethod
from typing import Dict

from pyraknet.bitstream import WriteStream
from ..game_object import Config, GameObject

class Component(ABC):
	def __setattr__(self, name: str, value: object) -> None:
		self.attr_changed(name)
		super().__setattr__(name, value)

	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		self.object = obj
		self._flags: Dict[str, str] = {}

	def attr_changed(self, name: str) -> None:
		"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""
		if hasattr(self, "_flags") and name in self._flags:
			setattr(self, self._flags[name], hasattr(self, name))
			self.object.signal_serialize()

	@abstractmethod
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass
