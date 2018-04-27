from pyraknet.bitstream import c_bool, c_int64, c_ubyte, c_uint, c_ushort
from luserver.tests.test_world import SessionWorldTest
from luserver.bitstream import WriteStream
from luserver.messages import WorldClientMsg, WorldServerMsg
from luserver.components.inventory import ItemType

class CharTest(SessionWorldTest):
	def set_up_db(self):
		super().set_up_db()
		self.db.colors = {0: True, 1: True, 2: True, 3: True, 5: True, 6: True, 7: True, 8: True, 9: True, 10: True, 11: True, 12: False, 13: True, 14: True, 15: True, 16: True, 17: False, 18: False, 19: False, 36: False, 42: False, 43: False, 45: False, 46: False, 47: False, 48: False, 49: False, 51: False, 52: False, 53: False, 63: False, 65: False, 71: False, 75: False, 77: False, 81: False, 84: True, 87: False, 88: False, 89: False, 93: False, 96: True, 105: False, 113: False, 119: False, 123: False, 130: False, 142: False, 143: False, 146: False, 147: False, 150: False, 151: False}
		self.db.components_registry[4084] = [(2, 3506), (11, 1147)]
		self.db.components_registry[2515] = [(2, 3342), (11, 914)]
		self.db.item_component = {914: (100, 7, 1, ()), 1147: (100, 15, 1, ())}
		self.db.item_sets = []

	def test_character_list(self):
		request = WriteStream()
		request.write_header(WorldServerMsg.CharacterListRequest)
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		resp = WriteStream()
		resp.write_header(WorldClientMsg.CharacterList)
		resp.write(c_ubyte(1))
		resp.write(c_ubyte(0))
		for char in self.player.char.account.characters.values():
			# currently not implemented
			pending_name = ""
			name_rejected = False
			is_ftp = False
			resp.write(c_int64(char.object_id))
			resp.write(bytes(4))
			resp.write(char.name, allocated_length=33)
			resp.write(pending_name, allocated_length=33)
			resp.write(c_bool(name_rejected))
			resp.write(c_bool(is_ftp))
			resp.write(bytes(10))
			resp.write(c_uint(char.char.shirt_color))
			resp.write(bytes(4))

			resp.write(c_uint(char.char.pants_color))
			resp.write(c_uint(char.char.hair_style))
			resp.write(c_uint(char.char.hair_color))
			resp.write(bytes(8))
			resp.write(c_uint(char.char.eyebrow_style))
			resp.write(c_uint(char.char.eye_style))
			resp.write(c_uint(char.char.mouth_style))
			resp.write(bytes(4))
			resp.write(c_ushort(char.char.world[0]))
			resp.write(c_ushort(char.char.world[1]))
			resp.write(c_uint(char.char.world[2]))
			resp.write(bytes(8))
			resp.write(c_ushort(len(char.inventory.equipped[-1])))
			for item in char.inventory.equipped[-1]:
				resp.write(c_uint(item.lot))
		self.assert_sent(resp)

	def test_create_char(self):
		request = WriteStream()
		request.write_header(WorldServerMsg.CharacterCreateRequest)
		request.write("charname", allocated_length=33)
		request.write(c_uint(1))
		request.write(c_uint(2))
		request.write(c_uint(3))
		request.write(bytes(9))
		request.write(c_uint(1))
		request.write(c_uint(2))
		request.write(c_uint(3))
		request.write(c_uint(4))
		request.write(c_uint(5))
		request.write(bytes(8))
		request.write(c_uint(6))
		request.write(c_uint(7))
		request.write(c_uint(8))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		chars = self.player.char.account.characters
		self.assertEqual(len(chars), 2)
		new_char = chars["charname"]
		self.assertEqual(new_char.name, "charname")
		shirt = None
		pants = None
		for item in new_char.inventory.items:
			if item is not None:
				if item.item_type == ItemType.Chest:
					shirt = item
				elif item.item_type == ItemType.Pants:
					pants = item
		self.assertIsNotNone(shirt)
		self.assertIsNotNone(pants)
		self.assertEqual(shirt.lot, 4084)
		self.assertEqual(pants.lot, 2515)
		self.assertEqual(new_char.char.hair_style, 4)
		self.assertEqual(new_char.char.hair_color, 5)
		self.assertEqual(new_char.char.eyebrow_style, 6)
		self.assertEqual(new_char.char.eye_style, 7)
		self.assertEqual(new_char.char.mouth_style, 8)

	def test_delete_char(self):
		request = WriteStream()
		request.write_header(WorldServerMsg.CharacterDeleteRequest)
		request.write(c_int64(self.player.object_id))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		self.assertEqual(len(self.server.accounts[self.ADDRESS].characters), 0)

	def test_enter_world(self):
		self.server.accounts[self.ADDRESS].selected_char_name = ""
		request = WriteStream()
		request.write_header(WorldServerMsg.EnterWorld)
		request.write(c_int64(self.player.object_id))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		self.assertEqual(self.server.accounts[self.ADDRESS].selected_char_name, self.player.name)
