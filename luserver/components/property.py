from pyraknet.bitstream import c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from ..amf3 import AMF3
from ..game_object import GameObject
from ..messages import broadcast, single, Serializable, Sequence
from ..world import server
from ..math.vector import Vector3
from .component import Component

class PropertyData(Serializable):
	def __init__(self):
		self.owner = None
		self.path = []

	def serialize(self, out):
		out.write(c_int64(0))
		out.write(c_int(25166))
		out.write(c_ushort(0))
		out.write(c_ushort(0))
		out.write(c_uint(0))
		out.write("", length_type=c_uint)
		out.write("", length_type=c_uint)
		out.write(self.owner.name, length_type=c_uint)
		out.write(c_int64(self.owner.object_id))
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_uint64(0))
		out.write(c_uint(0))
		out.write(c_uint64(0))
		out.write("", length_type=c_uint)
		out.write("", length_type=c_uint)
		out.write("", length_type=c_uint)
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_ubyte(0))
		out.write(c_uint64(0))
		out.write(c_uint(0))
		out.write("", length_type=c_uint)
		out.write(c_uint64(0))
		out.write(c_uint(0))
		out.write(c_uint(0))
		out.write(c_float(0))
		out.write(c_float(0))
		out.write(c_float(0))
		out.write(c_float(1000))
		out.write(c_uint64(0))
		out.write(c_ubyte(0))
		out.write(c_uint(len(self.path)))
		for coord in self.path:
			out.write(c_float(coord[0]))
			out.write(c_float(coord[1]))
			out.write(c_float(coord[2]))

	def deserialize(self, data):
		data.read(c_int64)
		data.read(c_int)
		data.read(c_ushort)
		data.read(c_ushort)
		data.read(c_uint)
		data.read(str, length_type=c_uint)
		data.read(str, length_type=c_uint)
		data.read(str, length_type=c_uint)
		data.read(c_int64)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_uint64)
		data.read(c_uint)
		data.read(c_uint64)
		data.read(str, length_type=c_uint)
		data.read(str, length_type=c_uint)
		data.read(str, length_type=c_uint)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_ubyte)
		data.read(c_uint64)
		data.read(c_uint)
		data.read(str, length_type=c_uint)
		data.read(c_uint64)
		data.read(c_uint)
		data.read(c_uint)
		data.read(c_float)
		data.read(c_float)
		data.read(c_float)
		data.read(c_float)
		data.read(c_uint64)
		data.read(c_ubyte)
		for _ in range(data.read(c_uint)):
			data.read(c_float)
			data.read(c_float)
			data.read(c_float)

		return PropertyData()

class PropertySelectQueryProperty(Serializable):
	def __init__(self):
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

	def serialize(self, out):
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
	def deserialize(data):
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
	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.property_entrance_begin(player=player)
		player.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "property_menu"}))
		return True

	def enter_property1(self, player, index:c_int=None, return_to_zone:bool=True):
		clone_id = 0
		if not return_to_zone and index == -1:
			clone_id = player.char.clone_id
		for model in player.inventory.models:
			if model is not None and model.lot == 6416:
				player.char.traveling_rocket = model.module_lots
				self.fire_event_client_side(args="RocketEquipped", obj=model, sender=player, param1=clone_id)
				break

	def property_entrance_sync(self, player, include_null_address:bool=None, include_null_description:bool=None, players_own:bool=None, update_ui:bool=None, num_results:c_int=None, reputation_time:c_int=None, sort_method:c_int=None, start_index:c_int=None, filter_text:bytes=None):
		my_property = PropertySelectQueryProperty()
		#my_property.clone_id = player.char.clone_id
		#my_property.is_owned = True

		self.property_select_query(nav_offset=0, there_are_more=False, my_clone_id=0, has_featured_property=False, was_friends=False, properties=[my_property], player=player)

	@single
	def property_select_query(self, nav_offset:c_int=None, there_are_more:bool=None, my_clone_id:c_int=None, has_featured_property:bool=None, was_friends:bool=None, properties:Sequence[c_uint, PropertySelectQueryProperty]=None):
		pass

	@broadcast
	def fire_event_client_side(self, args:str=None, obj:GameObject=None, param1:c_int64=0, param2:c_int=-1, sender:GameObject=None):
		pass

	@single
	def property_entrance_begin(self):
		pass

class PropertyManagementComponent(Component):
	def serialize(self, out, is_creation):
		pass

	@single # this is actually @broadcast but it's not needed and this packet is particularly large so i'm setting this to single
	def download_property_data(self, data:PropertyData=None):
		pass

	def query_property_data(self, player):
		if server.world_id[0] not in server.db.property_template:
			return
		property = PropertyData()
		property.owner = player
		property.path = server.db.property_template[server.world_id[0]]

		self.download_property_data(property, player=player)

	def start_building_with_item(self, player, first_time:bool=True, success:bool=None, source_bag:c_int=None, source_id:c_int64=None, source_lot:c_int=None, source_type:c_int=None, target_id:c_int64=None, target_lot:c_int=None, target_pos:Vector3=None, target_type:c_int=None):
		# source is item used for starting, target is module dragged on
		assert first_time
		assert not success
		if source_type == 1:
			source_type = 4

		player.char.start_arranging_with_item(first_time, self.object, player.physics.position, source_bag, source_id, source_lot, source_type, target_id, target_lot, target_pos, target_type)

	def set_build_mode(self, start:bool=None, distance_type:c_int=-1, mode_paused:bool=False, mode_value:c_int=1, player_id:c_int64=None, start_pos:Vector3=Vector3.zero):
		server.world_control_object.script.on_build_mode(start)
		self.set_build_mode_confirmed(start, False, mode_paused, mode_value, player_id, start_pos)

	@broadcast
	def set_build_mode_confirmed(self, start:bool=None, warn_visitors:bool=True, mode_paused:bool=False, mode_value:c_int=1, player_id:c_int64=None, start_pos:Vector3=Vector3.zero):
		pass

class PropertyVendorComponent(Component):
	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.open_property_vendor(player=player)

	@single # this is actually @broadcast but it's not needed and this packet is particularly large so i'm setting this to single
	def download_property_data(self, data:PropertyData=None):
		pass

	def query_property_data(self, player):
		if server.world_id[0] not in server.db.property_template:
			return
		property = PropertyData()
		property.owner = player
		property.path = server.db.property_template[server.world_id[0]]

		self.download_property_data(property, player=player)

	@single
	def open_property_vendor(self):
		pass

	def buy_from_vendor(self, player, confirmed:bool=False, count:c_int=1, item:c_int=None):
		# seems to actually add a 3188 property item to player's inventory?
		self.property_rental_response(clone_id=0, code=0, property_id=0, rentdue=0, player=player) # not really implemented
		player.char.set_flag(True, 108)
		server.world_control_object.script.on_property_rented(player)

	@single
	def property_rental_response(self, clone_id:c_uint=None, code:c_int=None, property_id:c_int64=None, rentdue:c_int64=None):
		pass
