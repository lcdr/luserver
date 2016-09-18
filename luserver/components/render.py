from ..bitstream import c_bit, c_float, c_int, c_int64
from .component import Component

class RenderComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.render = self

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_int(0))

	def play_f_x_effect(self, address, effect_id:c_int=-1, effect_type:"wstr"=None, scale:c_float=1, name:"str"=None, priority:c_float=1, secondary:c_int64=0, serialize:c_bit=True):
		pass

	def stop_f_x_effect(self, address, kill_immediate:c_bit=None, name:"str"=None):
		pass

	def play_embedded_effect_on_all_clients_near_object(self, address, effect_name:"wstr"=None, from_object_id:c_int64=None, radius:c_float=None):
		pass

	def play_n_d_audio_emitter(self, address, callback_message_data:c_int64=0, emitter_id:c_int=0, event_guid:"str"=None, meta_event_name:"str"=None, result:c_bit=False, target_object_id_for_ndaudio_callback_messages:c_int64=0):
		pass
