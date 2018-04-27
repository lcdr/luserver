
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
from typing import Tuple

from pyraknet.bitstream import c_int64, c_bool, c_ubyte, c_uint, c_ushort, ReadStream
from pyraknet.messages import Address
from ..bitstream import WriteStream
from ..game_object import Player
from ..messages import WorldClientMsg, WorldServerMsg
from ..world import server

log = logging.getLogger(__name__)

class _CharacterCreateReturnCode:
	Success = 0
	GeneralFailure = 1 # I'm just going to use this as general failure indicator
	NameNotAllowed = 2
	PredefinedNameInUse = 3
	CustomNameInUse = 4

class _CharacterDeleteReturnCode:
	Success = 1

_PANTS_LOT = {
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
	def __init__(self) -> None:
		server.register_handler(WorldServerMsg.CharacterListRequest, self._on_character_list_request)
		server.register_handler(WorldServerMsg.CharacterCreateRequest, self._on_character_create_request)
		server.register_handler(WorldServerMsg.CharacterDeleteRequest, self._on_character_delete_request)
		server.register_handler(WorldServerMsg.EnterWorld, self._on_enter_world)

	def _on_character_list_request(self, data: ReadStream, address: Address) -> None:
		try:
			selected_char = server.accounts[address].selected_char()

			if server.world_id[0] != 0:
				server.replica_manager.destruct(selected_char)
		except KeyError:
			pass

		server.conn.sync()
		characters = server.accounts[address].characters
		log.info("sending %i characters", len(characters))
		character_list = [i[1] for i in sorted(characters.items(), key=lambda x: x[0])]

		response = WriteStream()
		response.write_header(WorldClientMsg.CharacterList)
		response.write(c_ubyte(len(characters)))
		try:
			selected = character_list.index(server.accounts[address].selected_char())
		except KeyError:
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

	def _on_character_create_request(self, request: ReadStream, address: Address) -> None:
		account = server.accounts[address]
		char_name = request.read(str, allocated_length=33)
		predef_name_ids = request.read(c_uint), request.read(c_uint), request.read(c_uint)

		if char_name == "":
			char_name = self._predef_to_name(predef_name_ids)

		return_code = _CharacterCreateReturnCode.Success

		all_characters = [j for i in server.db.accounts.values() for j in i.characters.values()]
		for char in all_characters:
			if char.name == char_name:
				return_code = _CharacterCreateReturnCode.CustomNameInUse
				break

		try:
			if return_code == _CharacterCreateReturnCode.Success:
				new_char = Player(server.new_object_id())
				new_char.name = char_name
				new_char.char.account = account
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

				shirt = new_char.inventory.add_item(self._shirt_to_lot(new_char.char.shirt_color, new_char.char.shirt_style), notify_client=False)
				pants = new_char.inventory.add_item(_PANTS_LOT[new_char.char.pants_color], notify_client=False)
				new_char.inventory.on_equip_inventory(item_to_equip=shirt.object_id)
				new_char.inventory.on_equip_inventory(item_to_equip=pants.object_id)

				characters = account.characters
				characters[char_name] = new_char
				account.selected_char_name = char_name
				server.conn.transaction_manager.commit()
				log.info("Creating new character %s", char_name)
		except Exception:
			import traceback
			traceback.print_exc()
			return_code = _CharacterCreateReturnCode.GeneralFailure
			server.conn.sync()

		response = WriteStream()
		response.write_header(WorldClientMsg.CharacterCreateResponse)
		response.write(c_ubyte(return_code))
		server.send(response, address)

		if return_code == _CharacterCreateReturnCode.Success:
			self._on_character_list_request(ReadStream(b""), address)

	def _on_character_delete_request(self, request: ReadStream, address: Address) -> None:
		characters = server.accounts[address].characters
		char_id = request.read(c_int64)

		for char in characters:
			if characters[char].object_id == char_id:
				log.info("Deleting character %s", char)
				del characters[char]
				server.conn.transaction_manager.commit()
				break

		response = WriteStream()
		response.write_header(WorldClientMsg.CharacterDeleteResponse)
		response.write(c_ubyte(_CharacterDeleteReturnCode.Success))
		server.send(response, address)

		# todo: delete property

	def _on_enter_world(self, request: ReadStream, address: Address) -> None:
		char_id = request.read(c_int64)

		characters = server.accounts[address].characters
		selected_char_name = [key for key, value in characters.items() if value.object_id == char_id][0]
		server.accounts[address].selected_char_name = selected_char_name
		selected_char = server.accounts[address].selected_char()
		selected_char.char.address = address
		selected_char.char.online = True

		if selected_char.char.world[0] == 0:
			asyncio.ensure_future(selected_char.char.transfer_to_world((1000, 0, 0), respawn_point_name=""))
		else:
			asyncio.ensure_future(selected_char.char.transfer_to_world(selected_char.char.world, include_self=True))

	def _shirt_to_lot(self, color: int, style: int) -> int:
		# The LOTs for the shirts are for some reason in two batches of IDs
		lot_start_1 = 4048
		lot_start_2 = 5729
		num_styles_1 = 34
		num_styles_2 = 6

		cc_color_index = self._character_create_color_index(color)

		if 0 < style < 35:
			return lot_start_1 + cc_color_index * num_styles_1 + style
		if 34 < style < 41:
			return lot_start_2 + cc_color_index * num_styles_2 + style-34
		raise ValueError(style)

	def _character_create_color_index(self, color: int) -> int:
		index = 0
		sorted_colors = [i for i in sorted(server.db.colors.items(), key=lambda x: x[0])]
		for col, valid_characters in sorted_colors:
			if col == color:
				break
			if valid_characters:
				index += 1
		return index

	def _predef_to_name(self, predef_name_ids: Tuple[int, int, int]) -> str:
		name = ""
		for name_type, name_id in enumerate(predef_name_ids):
			name += server.db.predef_names[name_type][name_id]

		return name
