from pyraknet.bitstream import c_bit, c_int, c_int64
from .. ldf import LDF
from ..game_object import broadcast, GameObject
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
			out.write(c_bit(bool(self.script_network_vars)))
			if self.script_network_vars:
				out.write(self.script_network_vars.to_bitstream())

	def set_network_var(self, name, data_type, value):
		# theoretically this could be buffered to only send one message when multiple variables are set but is that worth it?
		self.script_network_vars.ldf_set(name, data_type, value)
		temp_ldf = LDF()
		temp_ldf.ldf_set(name, data_type, value)
		self.script_network_var_update(temp_ldf)

	@broadcast
	def script_network_var_update(self, script_vars:LDF=None):
		pass

	@broadcast
	def notify_client_object(self, name:str=None, param1:c_int=None, param2:c_int=None, param_obj:GameObject=None, param_str:bytes=None):
		pass

	@broadcast
	def fire_event_client_side(self, args:str=None, obj:GameObject=None, param1:c_int64=0, param2:c_int=-1, sender:GameObject=None):
		pass
