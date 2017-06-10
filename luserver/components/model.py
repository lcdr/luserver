from ..bitstream import c_bit, c_float, c_int
from ..ldf import LDFDataType
from .component import Component

class ModelComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		if hasattr(self.object, "pet"):
			return

		self.object.config.ldf_set("userModelID", LDFDataType.INT64_9, self.object.lot)
		self.object.config.ldf_set("propertyObjectID", LDFDataType.BOOLEAN, True)
		self.object.config.ldf_set("componentWhitelist", LDFDataType.INT32, 1)
		self.object.config.ldf_set("modelType", LDFDataType.INT32, -1)

	def serialize(self, out, is_creation):
		if hasattr(self.object, "pet"):
			return
		out.write(c_bit(True))
		out.write(c_bit(False))
		out.write(c_int(-1))
		out.write(c_float(self.object.physics.position.x))
		out.write(c_float(self.object.physics.position.y))
		out.write(c_float(self.object.physics.position.z))
		out.write(c_float(self.object.physics.rotation.w))
		out.write(c_float(self.object.physics.position.x))
		out.write(c_float(self.object.physics.position.y))
		out.write(c_float(self.object.physics.position.z))
		out.write(c_bit(True))
		out.write(c_int(0))
		out.write(c_bit(True))
		out.write(c_bit(False))
