from pyraknet.bitstream import c_bit, c_float, c_int, WriteStream
from ..game_object import Config, GameObject
from ..ldf import LDFDataType
from .component import Component

class ModelComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		if hasattr(self.object, "pet"):
			return

		self.object.config.ldf_set("userModelID", LDFDataType.INT64_9, self.object.lot)
		self.object.config.ldf_set("propertyObjectID", LDFDataType.BOOLEAN, True)
		self.object.config.ldf_set("componentWhitelist", LDFDataType.INT32, 1)
		self.object.config.ldf_set("modelType", LDFDataType.INT32, -1)

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if hasattr(self.object, "pet"):
			return
		out.write(c_bit(True))
		out.write(c_bit(False))
		out.write(c_int(-1))
		out.write(self.object.physics.position)
		out.write(c_float(self.object.physics.rotation.w))
		out.write(c_float(self.object.physics.rotation.x))
		out.write(c_float(self.object.physics.rotation.y))
		out.write(c_float(self.object.physics.rotation.z))
		out.write(c_bit(True))
		out.write(c_int(0))
		out.write(c_bit(True))
		out.write(c_bit(False))
