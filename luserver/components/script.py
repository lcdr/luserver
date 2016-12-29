from .. ldf import LDF
from ..bitstream import c_bit, c_int, c_int64
from ..messages import broadcast
from .component import Component

class ScriptComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.script = self
		self.script_vars = {}
		if "script_vars" in set_vars:
			self.script_vars = set_vars["script_vars"]

		self.script_network_vars = LDF()

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(self.script_network_vars))
			if self.script_network_vars:
				out.write(self.script_network_vars.to_bitstream())

	@broadcast
	def script_network_var_update(self, script_vars:LDF=None):
		pass

	@broadcast
	def notify_client_object(self, name:"wstr"=None, param1:c_int=None, param2:c_int=None, param_obj:c_int64=None, param_str:"str"=None):
		pass

	@broadcast
	def fire_event_client_side(self, args:"wstr"=None, obj:c_int64=None, param1:c_int64=0, param2:c_int=-1, sender_id:c_int64=None):
		pass
