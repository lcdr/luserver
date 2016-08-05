from ..bitstream import c_bit

class ScriptComponent:
	def __init__(self, comp_id):
		self.script_vars = {}

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))

	def script_network_var_update(self, address, vars:"ldf"=None):
		pass