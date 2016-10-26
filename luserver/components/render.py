from ..bitstream import c_bit, c_float, c_int, c_int64, c_ubyte, c_uint
from .component import Component

class RenderComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.render = self
		self.effects = {}

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_uint(len(self.effects)))
			for name, effect_values in self.effects.items():
				effect_id, effect_type = effect_values
				out.write(name, char_size=1, length_type=c_ubyte)
				out.write(c_int(effect_id))
				out.write(effect_type, length_type=c_ubyte)
				out.write(c_float(1))
				out.write(c_int64(0))

	def play_animation(self, address, animation_id:"wstr"=None, expect_anim_to_exist:c_bit=True, play_immediate:c_bit=None, trigger_on_complete_msg:c_bit=False, priority:c_float=2, f_scale:c_float=1):
		pass

	def play_f_x_effect(self, address, effect_id:c_int=-1, effect_type:"wstr"=None, scale:c_float=1, name:"str"=None, priority:c_float=1, secondary:c_int64=0, serialize:c_bit=True):
		self.effects[name] = effect_id, effect_type

	def stop_f_x_effect(self, address, kill_immediate:c_bit=None, name:"str"=None):
		if name in self.effects:
			del self.effects[name]

	def play_embedded_effect_on_all_clients_near_object(self, address, effect_name:"wstr"=None, from_object_id:c_int64=None, radius:c_float=None):
		pass

	def play_n_d_audio_emitter(self, address, callback_message_data:c_int64=0, emitter_id:c_int=0, event_guid:"str"=None, meta_event_name:"str"=None, result:c_bit=False, target_object_id_for_ndaudio_callback_messages:c_int64=0):
		pass
