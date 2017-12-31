from abc import ABC, abstractmethod

class Component(ABC):
	def __setattr__(self, name, value):
		self.attr_changed(name)
		super().__setattr__(name, value)

	def __init__(self, obj, set_vars, comp_id):
		self.object = obj
		self._flags = {}

	def attr_changed(self, name: str) -> None:
		"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""
		if hasattr(self, "_flags") and name in self._flags:
			setattr(self, self._flags[name], hasattr(self, name))
			self.object.signal_serialize()

	@abstractmethod
	def serialize(self, out, is_creation):
		pass
