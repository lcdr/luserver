from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import c_int64, EB, EI
from .component import Component

class BouncerComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))

	def on_bounce_notification(self, object_id_bounced:c_int64=EI, object_id_bouncer:c_int64=EI, success:bool=EB) -> None:
		pass
