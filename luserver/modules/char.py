
class Color:
	BrightRed = 0
	BrightBlue = 1
	Yellow = 2 # not normally available
	DarkGreen = 3
	# 4 = white/unused
	BrightOrange = 5
	Black = 6
	DarkStoneGrey = 7
	MediumStoneGrey = 8
	ReddishBrown = 9
	White = 10
	MediumBlue = 11
	Lime = 12 # not normally available
	DarkRed = 13
	EarthBlue = 14
	EarthGreen = 15
	BrickYellow = 16
	Pink = 17 # not normally available
	OtherYellow = 18 # not normally available
	OtherOrange = 19 # not normally available
	SandBlue = 84
	SandGreen = 96

class EyeStyle:
	# incomplete
	# all not normally available
	Bob = 9
	Scar = 24
	Ninja = 30
	Cyborg = 33
	BandAid = 35
	Sunglasses = 36
	BobEyebrows = 38
	BlueHeadWhiteEyes = 41
	FullCyborg = 43
	Robot = 44
	RedEyes = 45
	Monocle = 49
	BlueEyes = 53

class MouthStyle:
	# incomplete
	# all not normally available
	HeadSet = 39
	Mask = 40
	LargeSmile = 45
	Vampire = 46 # also makes face white
	Robot = 48 # also makes face grey
	WhiteFace = 51

import asyncio
import logging

import persistent.wref

from ..bitstream import BitStream, c_int64, c_bool, c_ubyte, c_uint, c_ushort
from ..game_object import PersistentObject
from ..messages import WorldClientMsg, WorldServerMsg
from ..world import server

log = logging.getLogger(__name__)

class CharacterCreateReturnCode:
	Success = 0
	GeneralFailure = 1 # I'm just going to use this as general failure indicator
	NameNotAllowed = 2
	PredefinedNameInUse = 3
	CustomNameInUse = 4

class CharacterDeleteReturnCode:
	Success = 1

pants_lot = {
	Color.BrightRed: 2508,
	Color.BrightOrange: 2509,
	Color.BrickYellow: 2511,
	Color.MediumBlue: 2513,
	Color.SandGreen: 2514,
	Color.DarkGreen: 2515,
	Color.EarthGreen: 2516,
	Color.EarthBlue: 2517,
	Color.BrightBlue: 2519,
	Color.SandBlue: 2520,
	Color.DarkStoneGrey: 2521,
	Color.MediumStoneGrey: 2522,
	Color.White: 2523,
	Color.Black: 2524,
	Color.ReddishBrown: 2526,
	Color.DarkRed: 2527}

class CharHandling:
	def __init__(self):
		server.char = self
		server.register_handler(WorldServerMsg.CharacterListRequest, self.on_character_list_request)
		server.register_handler(WorldServerMsg.CharacterCreateRequest, self.on_character_create_request)
		server.register_handler(WorldServerMsg.CharacterDeleteRequest, self.on_character_delete_request)
		server.register_handler(WorldServerMsg.EnterWorld, self.on_enter_world)

	def on_character_list_request(self, data, address):
		selected = server.accounts[address].characters.selected()

		if server.world_id[0] != 0:
			server.replica_manager.destruct(selected)

		server.conn.sync()
		characters = server.accounts[address].characters
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

			response.write(char.name, allocated_length=33)
			response.write(pending_name, allocated_length=33)
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

			response.write(c_ushort(len(char.inventory.equipped[-1])))
			for item in char.inventory.equipped[-1]:
				response.write(c_uint(item.lot))

		server.send(response, address)

	def on_character_create_request(self, request, address):
		char_name = request.read(str, allocated_length=33)
		predef_name_ids = request.read(c_uint), request.read(c_uint), request.read(c_uint)

		if char_name == "":
			char_name = self.predef_to_name(predef_name_ids)

		return_code = CharacterCreateReturnCode.Success

		all_characters = [j for i in server.db.accounts.values() for j in i.characters.values()]
		for char in all_characters:
			if char.name == char_name:
				return_code = CharacterCreateReturnCode.CustomNameInUse
				break

		try:
			if return_code == CharacterCreateReturnCode.Success:
				new_char = PersistentObject(1, server.new_object_id())
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
				new_char.inventory.equip_inventory(item_to_equip=shirt.object_id)
				new_char.inventory.equip_inventory(item_to_equip=pants.object_id)

				characters = server.accounts[address].characters
				characters[char_name] = new_char
				characters.selected = persistent.wref.WeakRef(new_char)
				server.conn.transaction_manager.commit()
		except Exception:
			import traceback
			traceback.print_exc()
			return_code = CharacterCreateReturnCode.GeneralFailure
			server.conn.sync()

		response = BitStream()
		response.write_header(WorldClientMsg.CharacterCreateResponse)
		response.write(c_ubyte(return_code))
		server.send(response, address)

		if return_code == CharacterCreateReturnCode.Success:
			self.on_character_list_request(b"", address)

	def on_character_delete_request(self, request, address):
		characters = server.accounts[address].characters
		char_id = request.read(c_int64)

		for char in characters:
			if characters[char].object_id == char_id:
				del characters[char]
				server.conn.transaction_manager.commit()
				break

		response = BitStream()
		response.write_header(WorldClientMsg.CharacterDeleteResponse)
		response.write(c_ubyte(CharacterDeleteReturnCode.Success))
		server.send(response, address)

		# todo: delete property

	def on_enter_world(self, request, address):
		char_id = request.read(c_int64)

		characters = server.accounts[address].characters
		selected_char = [i for i in characters.values() if i.object_id == char_id][0]
		characters.selected = persistent.wref.WeakRef(selected_char)
		selected_char.char.address = address
		selected_char.char.online = True

		server.conn.transaction_manager.commit()

		if selected_char.char.world[0] == 0:
			selected_char.char.world = 1000, 0, 0
			asyncio.ensure_future(selected_char.char.transfer_to_world(selected_char.char.world, respawn_point_name=""))
		else:
			asyncio.ensure_future(selected_char.char.transfer_to_world(selected_char.char.world, include_self=True))

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
		sorted_colors = [i for i in sorted(server.db.colors.items(), key=lambda x: x[0])]
		for col, valid_characters in sorted_colors:
			if col == color:
				break
			if valid_characters:
				index += 1
		return index

	def predef_to_name(self, predef_name_ids):
		name = ""
		for name_type, name_id in enumerate(predef_name_ids):
			name += server.db.predef_names[name_type][name_id]

		return name
