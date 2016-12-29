import asyncio

from ..bitstream import c_bit, c_float, c_int, c_int64, c_uint
from .component import Component

class ScriptedActivityComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.scripted_activity = self
		self._flags["players"] = "activity_flag"
		self.players = []
		self.comp_id = comp_id

	def serialize(self, out, is_creation):
		out.write(c_bit(self.activity_flag))
		if self.activity_flag:
			out.write(c_uint(len(self.players)))
			for object_id in self.players:
				out.write(c_int64(object_id))
				for _ in range(10):
					out.write(c_float(0))
			self.activity_flag = False

	def activity_start(self, address):
		pass

	def message_box_respond(self, address, button:c_int=None, identifier:"wstr"=None, user_data:"wstr"=None):
		if identifier == "LobbyReady" and button == 1:
			player = self.object._v_server.accounts[address].characters.selected()
			activity = self.object._v_server.db.activities[self.comp_id]
			asyncio.ensure_future(player.char.transfer_to_world((activity[0], 0, 0)))
