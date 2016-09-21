from ..bitstream import c_bit, c_int, c_int64
from .component import Component

class ScriptComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.script = self
		self.script_vars = {}
		if "script_vars" in set_vars:
			self.script_vars = set_vars["script_vars"]

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))

	def script_network_var_update(self, address, script_vars:"ldf"=None):
		pass

	def notify_client_object(self, address, name:"wstr"=None, param1:c_int=None, param2:c_int=None, param_obj:c_int64=None, param_str:"str"=None):
		pass
