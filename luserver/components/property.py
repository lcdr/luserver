from typing import cast, List, Optional, Tuple

from bitstream import c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, ReadStream, Serializable, WriteStream
from ..amf3 import AMF3
from ..game_object import broadcast, E, EB, EBY, EI, EO, ES, EV, GameObject, Player, Sequence, single
from ..game_object import c_int as c_int_
from ..game_object import c_uint as c_uint_
from ..game_object import c_int64 as c_int64_
from ..world import server
from ..math.vector import Vector3
from .component import Component

class PropertyData(Serializable):
	def __init__(self) -> None:
		self.owner: Player = None
		self.path: List[Tuple[float, float, float]] = []

	def serialize(self, stream: WriteStream) -> None:
		stream.write(c_int64(0))
		stream.write(c_int(25166))
		stream.write(c_ushort(0))
		stream.write(c_ushort(0))
		stream.write(c_uint(0))
		stream.write("", length_type=c_uint)
		stream.write("", length_type=c_uint)
		stream.write(self.owner.name, length_type=c_uint)
		stream.write(c_int64(self.owner.object_id))
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_uint64(0))
		stream.write(c_uint(0))
		stream.write(c_uint64(0))
		stream.write("", length_type=c_uint)
		stream.write("", length_type=c_uint)
		stream.write("", length_type=c_uint)
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_ubyte(0))
		stream.write(c_uint64(0))
		stream.write(c_uint(0))
		stream.write("", length_type=c_uint)
		stream.write(c_uint64(0))
		stream.write(c_uint(0))
		stream.write(c_uint(0))
		stream.write(c_float(0))
		stream.write(c_float(0))
		stream.write(c_float(0))
		stream.write(c_float(1000))
		stream.write(c_uint64(0))
		stream.write(c_ubyte(0))
		stream.write(c_uint(len(self.path)))
		for coord in self.path:
			stream.write(c_float(coord[0]))
			stream.write(c_float(coord[1]))
			stream.write(c_float(coord[2]))

	def deserialize(self, stream: ReadStream) -> "PropertyData":
		stream.read(c_int64)
		stream.read(c_int)
		stream.read(c_ushort)
		stream.read(c_ushort)
		stream.read(c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(c_int64)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_uint64)
		stream.read(c_uint)
		stream.read(c_uint64)
		stream.read(str, length_type=c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_ubyte)
		stream.read(c_uint64)
		stream.read(c_uint)
		stream.read(str, length_type=c_uint)
		stream.read(c_uint64)
		stream.read(c_uint)
		stream.read(c_uint)
		stream.read(c_float)
		stream.read(c_float)
		stream.read(c_float)
		stream.read(c_float)
		stream.read(c_uint64)
		stream.read(c_ubyte)
		for _ in range(stream.read(c_uint)):
			stream.read(c_float)
			stream.read(c_float)
			stream.read(c_float)

		return PropertyData()

class PropertySelectQueryProperty(Serializable):
	def __init__(self) -> None:
		self.clone_id = 0
		self.owner_name = "Test owner name"
		self.name = "Test name"
		self.description = "Test description"
		self.reputation = 0
		self.is_bff = False
		self.is_friend = False
		self.is_moderated_approved = True
		self.is_alt = False
		self.is_owned = False
		self.access_type = 2
		self.date_last_published = 0
		self.performance_cost = 0

	def serialize(self, out: WriteStream) -> None:
		out.write(c_uint(self.clone_id))
		out.write(self.owner_name, length_type=c_uint)
		out.write(self.name, length_type=c_uint)
		out.write(self.description, length_type=c_uint)
		out.write(c_uint(self.reputation))
		out.write(c_bit(self.is_bff))
		out.write(c_bit(self.is_friend))
		out.write(c_bit(self.is_moderated_approved))
		out.write(c_bit(self.is_alt))
		out.write(c_bit(self.is_owned))
		out.write(c_uint(self.access_type))
		out.write(c_uint(self.date_last_published))
		out.write(c_uint64(self.performance_cost))

	@staticmethod
	def deserialize(data: ReadStream) -> "PropertySelectQueryProperty":
		obj = PropertySelectQueryProperty()
		obj.clone_id = data.read(c_uint)
		obj.owner_name = data.read(str, length_type=c_uint)
		obj.name = data.read(str, length_type=c_uint)
		obj.description = data.read(str, length_type=c_uint)
		obj.reputation = data.read(c_uint)
		obj.is_bff = data.read(c_bit)
		obj.is_friend = data.read(c_bit)
		obj.is_moderated_approved = data.read(c_bit)
		obj.is_alt = data.read(c_bit)
		obj.is_owned = data.read(c_bit)
		obj.access_type = data.read(c_uint)
		obj.date_last_published = data.read(c_uint)
		obj.performance_cost = data.read(c_uint64)
		return obj

class PropertyEntranceComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> bool:
		assert multi_interact_id is None
		self.property_entrance_begin(player=player)
		player.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "property_menu"}))
		return True

	def on_enter_property1(self, player: Player, index:c_int_=EI, return_to_zone:bool=True) -> None:
		clone_id = 0
		if not return_to_zone and index == -1:
			clone_id = player.char.clone_id
		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				player.char.traveling_rocket = model.module_lots
				self.fire_event_client_side(args="RocketEquipped", obj=model, sender=player, param1=clone_id)
				break

	def on_property_entrance_sync(self, player: Player, include_null_address:bool=EB, include_null_description:bool=EB, players_own:bool=EB, update_ui:bool=EB, num_results:c_int_=EI, reputation_time:c_int_=EI, sort_method:c_int_=EI, start_index:c_int_=EI, filter_text:bytes=EBY) -> None:
		my_property = PropertySelectQueryProperty()
		#my_property.clone_id = player.char.clone_id
		#my_property.is_owned = True

		self.property_select_query(nav_offset=0, there_are_more=False, my_clone_id=0, has_featured_property=False, was_friends=False, properties=[my_property], player=player)

	@single
	def property_select_query(self, nav_offset:c_int_=EI, there_are_more:bool=EB, my_clone_id:c_int_=EI, has_featured_property:bool=EB, was_friends:bool=EB, properties:Sequence[c_uint, PropertySelectQueryProperty]=E) -> None:
		pass

	@broadcast
	def fire_event_client_side(self, args:str=ES, obj:GameObject=EO, param1:c_int64_=0, param2:c_int_=-1, sender:GameObject=EO) -> None:
		pass

	@single
	def property_entrance_begin(self) -> None:
		pass

EPD = cast(PropertyData, E)

class PropertyManagementComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	@single # this is actually @broadcast but it's not needed and this packet is particularly large so i'm setting this to single
	def download_property_data(self, data:PropertyData=EPD) -> None:
		pass

	def on_query_property_data(self, player: Player) -> None:
		if server.world_id[0] not in server.db.property_template:
			return
		property = PropertyData()
		property.owner = player
		property.path = server.db.property_template[server.world_id[0]]

		self.download_property_data(property, player=player)

	def on_start_building_with_item(self, player: Player, first_time:bool=True, success:bool=EB, source_bag:c_int_=EI, source_id:c_int64_=EI, source_lot:c_int_=EI, source_type:c_int_=EI, target_id:c_int64_=EI, target_lot:c_int_=EI, target_pos:Vector3=EV, target_type:c_int_=EI) -> None:
		# source is item used for starting, target is module dragged on
		assert first_time
		assert not success
		if source_type == 1:
			source_type = 4

		player.char.start_arranging_with_item(first_time, self.object, player.physics.position, source_bag, source_id, source_lot, source_type, target_id, target_lot, target_pos, target_type)

	def on_set_build_mode(self, start:bool=EB, distance_type:c_int_=-1, mode_paused:bool=False, mode_value:c_int_=1, player_id:c_int64_=EI, start_pos:Vector3=Vector3.zero) -> None:
		server.world_control_object.script.on_build_mode(start)
		self.set_build_mode_confirmed(start, False, mode_paused, mode_value, player_id, start_pos)

	@broadcast
	def set_build_mode_confirmed(self, start:bool=EB, warn_visitors:bool=True, mode_paused:bool=False, mode_value:c_int_=1, player_id:c_int64_=EI, start_pos:Vector3=Vector3.zero) -> None:
		pass

class PropertyVendorComponent(Component):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		self.open_property_vendor(player=player)

	@single # this is actually @broadcast but it's not needed and this packet is particularly large so i'm setting this to single
	def download_property_data(self, data:PropertyData=EPD) -> None:
		pass

	def on_query_property_data(self, player: Player) -> None:
		if server.world_id[0] not in server.db.property_template:
			return
		property = PropertyData()
		property.owner = player
		property.path = server.db.property_template[server.world_id[0]]

		self.download_property_data(property, player=player)

	@single
	def open_property_vendor(self) -> None:
		pass

	def on_buy_from_vendor(self, player: Player, confirmed:bool=False, count:c_int_=1, item:c_int_=EI) -> None:
		# seems to actually add a 3188 property item to player's inventory?
		self.property_rental_response(clone_id=0, code=0, property_id=0, rentdue=0, player=player) # not really implemented
		player.char.set_flag(True, 108)
		server.world_control_object.script.on_property_rented(player)

	@single
	def property_rental_response(self, clone_id:c_uint_=EI, code:c_int_=EI, property_id:c_int64_=EI, rentdue:c_int64_=EI) -> None:
		pass
