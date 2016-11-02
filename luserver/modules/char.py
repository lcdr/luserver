import asyncio
import logging

import persistent.wref

from ..bitstream import BitStream, c_int64, c_bool, c_ubyte, c_uint, c_ushort
from ..game_object import PersistentObject
from ..messages import WorldClientMsg, WorldServerMsg
from .module import ServerModule

log = logging.getLogger(__name__)

class CharacterCreateReturnCode:
	Success = 0
	GeneralFailure = 1 # I'm just going to use this as general failure indicator
	NameNotAllowed = 2
	PredefinedNameInUse = 3
	CustomNameInUse = 4

class CharacterDeleteReturnCode:
	Success = 1

class Color:
	BrightRed = 0
	BrightBlue = 1
	DarkGreen = 3
	BrightOrange = 5
	Black = 6
	DarkStoneGrey = 7
	MediumStoneGrey = 8
	ReddishBrown = 9
	White = 10
	MediumBlue = 11
	DarkRed = 13
	EarthBlue = 14
	EarthGreen = 15
	BrickYellow = 16
	SandBlue = 84
	SandGreen = 96

pants_lot = {}
pants_lot[Color.BrightRed] = 2508
pants_lot[Color.BrightOrange] = 2509
pants_lot[Color.BrickYellow] = 2511
pants_lot[Color.MediumBlue] = 2513
pants_lot[Color.SandGreen] = 2514
pants_lot[Color.DarkGreen] = 2515
pants_lot[Color.EarthGreen] = 2516
pants_lot[Color.EarthBlue] = 2517
pants_lot[Color.BrightBlue] = 2519
pants_lot[Color.SandBlue] = 2520
pants_lot[Color.DarkStoneGrey] = 2521
pants_lot[Color.MediumStoneGrey] = 2522
pants_lot[Color.White] = 2523
pants_lot[Color.Black] = 2524
pants_lot[Color.ReddishBrown] = 2526
pants_lot[Color.DarkRed] = 2527

class CharHandling(ServerModule):
	def on_validated(self, address):
		self.server.register_handler(WorldServerMsg.CharacterListRequest, self.on_character_list_request, address)
		self.server.register_handler(WorldServerMsg.CharacterCreateRequest, self.on_character_create_request, address)
		self.server.register_handler(WorldServerMsg.CharacterDeleteRequest, self.on_character_delete_request, address)
		self.server.register_handler(WorldServerMsg.EnterWorld, self.on_enter_world, address)

	def on_character_list_request(self, data, address):
		selected = self.server.accounts[address].characters.selected()

		if self.server.world_id[0] != 0:
			self.server.destruct(selected)

		self.server.conn_sync()
		characters = self.server.accounts[address].characters
		log.info("sending %i characters", len(characters))
		character_list = [i[1] for i in sorted(characters.items(), key=lambda x: x[0])]

		response = BitStream()
		response.write_header(WorldClientMsg.CharacterList)
		response.write(c_ubyte(len(characters)))
		ref = characters.selected()
		try:
			selected = character_list.index(ref)
		except ValueError:
			selected = 0
		response.write(c_ubyte(selected))

		for char in character_list:
			# currently not implemented
			pending_name = ""
			name_rejected = False
			is_ftp = False

			response.write(c_int64(char.object_id))
			response.write(bytes(4))

			response.write(char.name, allocated_length=66)
			response.write(pending_name, allocated_length=66)
			response.write(c_bool(name_rejected))
			response.write(c_bool(is_ftp))
			response.write(bytes(10))

			response.write(c_uint(char.char.shirt_color))
			response.write(bytes(4))

			response.write(c_uint(char.char.pants_color))
			response.write(c_uint(char.char.hair_style))
			response.write(c_uint(char.char.hair_color))
			response.write(bytes(8))

			response.write(c_uint(char.char.eyebrow_style))
			response.write(c_uint(char.char.eye_style))
			response.write(c_uint(char.char.mouth_style))
			response.write(bytes(4))

			response.write(c_ushort(char.char.world[0]))
			response.write(c_ushort(char.char.world[1]))
			response.write(c_uint(char.char.world[2]))
			response.write(bytes(8))

			items = [i for i in char.inventory.items if i is not None and i.equipped]
			response.write(c_ushort(len(items)))
			for item in items:
				response.write(c_uint(item.lot))

		self.server.send(response, address)

	def on_character_create_request(self, request, address):
		char_name = request.read(str, allocated_length=66)
		predef_name_ids = request.read(c_uint), request.read(c_uint), request.read(c_uint)

		if char_name == "":
			char_name = self.predef_to_name(predef_name_ids)

		return_code = CharacterCreateReturnCode.Success

		all_characters = [j for i in self.server.db.accounts.values() for j in i.characters.values()]
		for char in all_characters:
			if char.name == char_name:
				return_code = CharacterCreateReturnCode.CustomNameInUse
				break

		try:
			if return_code == CharacterCreateReturnCode.Success:
				new_char = PersistentObject(self.server, 1, self.server.new_object_id())
				new_char.name = char_name
				new_char.char.address = address

				request.skip_read(9)
				new_char.char.shirt_color = request.read(c_uint)
				new_char.char.shirt_style = request.read(c_uint)
				new_char.char.pants_color = request.read(c_uint)
				new_char.char.hair_style = request.read(c_uint)
				new_char.char.hair_color = request.read(c_uint)
				request.skip_read(8)
				new_char.char.eyebrow_style = request.read(c_uint)
				new_char.char.eye_style = request.read(c_uint)
				new_char.char.mouth_style = request.read(c_uint)

				shirt = new_char.inventory.add_item_to_inventory(self.shirt_to_lot(new_char.char.shirt_color, new_char.char.shirt_style), notify_client=False)
				pants = new_char.inventory.add_item_to_inventory(pants_lot[new_char.char.pants_color], notify_client=False)
				new_char.inventory.equip_inventory(None, item_to_equip=shirt.object_id)
				new_char.inventory.equip_inventory(None, item_to_equip=pants.object_id)

				characters = self.server.accounts[address].characters
				characters[char_name] = new_char
				characters.selected = persistent.wref.WeakRef(new_char)
				self.server.commit()
		except Exception:
			import traceback
			traceback.print_exc()
			return_code = CharacterCreateReturnCode.GeneralFailure
			self.server.conn_sync()

		response = BitStream()
		response.write_header(WorldClientMsg.CharacterCreateResponse)
		response.write(c_ubyte(return_code))
		self.server.send(response, address)

		if return_code == CharacterCreateReturnCode.Success:
			self.on_character_list_request(b"", address)

	def on_character_delete_request(self, request, address):
		characters = self.server.accounts[address].characters
		char_id = request.read(c_int64)

		for char in characters:
			if characters[char].object_id == char_id:
				del characters[char]
				self.server.commit()
				break

		response = BitStream()
		response.write_header(WorldClientMsg.CharacterDeleteResponse)
		response.write(c_ubyte(CharacterDeleteReturnCode.Success))
		self.server.send(response, address)

		# todo: delete property

	def on_enter_world(self, request, address):
		char_id = request.read(c_int64)

		characters = self.server.accounts[address].characters
		selected_char = [i for i in characters.values() if i.object_id == char_id][0]
		characters.selected = persistent.wref.WeakRef(selected_char)
		selected_char.char.address = address
		selected_char._v_server = self.server
		selected_char.char.online = True

		if selected_char.char.world[0] == 0:
			selected_char.char.world = 1000, 0, 0

		self.server.commit()

		asyncio.ensure_future(selected_char.char.transfer_to_world(selected_char.char.world))

	def shirt_to_lot(self, color, style):
		# The LOTs for the shirts are for some reason in two batches of IDs
		lot_start_1 = 4048
		lot_start_2 = 5729
		amount_of_styles_1 = 34
		amount_of_styles_2 = 6

		cc_color_index = self.character_create_color_index(color)

		if 0 < style < 35:
			return lot_start_1 + cc_color_index * amount_of_styles_1 + style
		if 34 < style < 41:
			return lot_start_2 + cc_color_index * amount_of_styles_2 + style-34
		raise ValueError(style)

	def character_create_color_index(self, color):
		index = 0
		sorted_colors = [i for i in sorted(self.server.db.colors.items(), key=lambda x: x[0])]
		for col, valid_characters in sorted_colors:
			if col == color:
				break
			if valid_characters:
				index += 1
		return index

	def predef_to_name(self, predef_name_ids):
		name = ""
		for name_type, name_id in enumerate(predef_name_ids):
			name += self.server.db.predef_names[name_type][name_id]

		return name
