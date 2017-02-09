"""
For world server packet handling that is general enough not to be grouped in a specialized handling module.
"""
import functools
import inspect
import logging
import re
import xml.etree.ElementTree as ET

from ..ldf import LDF, LDFDataType
from ..bitstream import BitStream, c_bit, c_float, c_int64, c_uint, c_ushort
from ..messages import game_message_deserialize, GameMessage, WorldClientMsg, WorldServerMsg
from ..world import World
from ..components.mission import TaskType
from .module import ServerModule

log = logging.getLogger(__name__)

# Constant checksums that the client expects to verify map version
# (likely value of the last map revision)
checksum = {
	World.VentureExplorer: 0x20b8087c,
	World.ReturnToTheVentureExplorer: 0x26680a3c,
	World.AvantGardens: 0x49525511,
	World.AvantGardensSurvival: 0x538214e2,
	World.SpiderQueenBattle: 0xfd403da,
	World.BlockYard: 0xfd403da,
	World.AvantGrove: 0xa890303,
	World.NimbusStation: 0xda1e6b30,
	World.PetCove: 0x476e1330,
	World.VertigoLoop: 0x10fc0502,
	World.TheBattleOfNimbusStation: 0x7d40258,
	World.NimbusRock: 0x58d0191,
	World.NimbusIsle: 0x94f045d,
	World.GnarledForest: 0x12eac290,
	World.CannonCoveShootingGallery: 0xb7702ef,
	World.ChanteyShanty: 0x4b6015c,
	World.ForbiddenValley: 0x8519760d,
	World.ForbiddenValleyDragonBattle: 0x2f50187,
	World.DragonmawChasm: 0x81850f4e,
	World.RavenBluff: 0x3f00126,
	World.Starbase3001: 0x7c202ee,
	World.DeepFreeze: 0x2320106,
	World.RobotCity: 0x793037f,
	World.MoonBase: 0x43b01ad,
	World.Portabello: 0x181507dd,
	World.LEGOClub: 0x2040138,
	World.CruxPrime: 0x4b17a399,
	World.NexusTower: 0x9e4af43c,
	World.NinjagoMonastery: 0x4d692c74,
	World.BattleAgainstFrakjaw: 0x9eb00ef}

class GeneralHandling(ServerModule):
	def on_validated(self, address):
		self.server.register_handler(WorldServerMsg.LoadComplete, self.on_client_load_complete, address)
		self.server.register_handler(WorldServerMsg.PositionUpdate, self.on_position_update, address)
		self.server.register_handler(WorldServerMsg.GameMessage, self.on_game_message, address)
		player = self.server.accounts[address].characters.selected()
		if player is not None:
			player._v_server = self.server
			player.parent = None
			player.children = []
			player.parent_flag = False
			player.children_flag = False
			if self.server.world_id[0] != 0:
				self.send_load_world(self.server.world_id, address)

	def send_load_world(self, destination, address):
		world_id, world_instance, world_clone = destination
		player = self.server.accounts[address].characters.selected()

		load_world = BitStream()
		load_world.write_header(WorldClientMsg.LoadWorld)
		load_world.write(c_ushort(world_id))
		load_world.write(c_ushort(world_instance))
		load_world.write(c_uint(world_clone))
		load_world.write(c_uint(checksum[World(world_id)]))
		load_world.write(bytes(2))
		load_world.write(c_float(player.physics.position.x))
		load_world.write(c_float(player.physics.position.y))
		load_world.write(c_float(player.physics.position.z))
		load_world.write(bytes(4))
		self.server.send(load_world, address)

		player.char.world = destination

	def on_client_load_complete(self, data, address):
		player = self.server.accounts[address].characters.selected()

		chardata = BitStream()
		chardata.write_header(WorldClientMsg.CharacterData)

		root = ET.Element("obj")
		char_ = ET.SubElement(root, "char", cc=str(player.char.currency))
		unlocked_emotes = ET.SubElement(char_, "ue")
		for emote_id in player.char.unlocked_emotes:
			ET.SubElement(unlocked_emotes, "e", id=str(emote_id))
		inv = ET.SubElement(root, "inv")
		bag = ET.SubElement(inv, "bag")
		ET.SubElement(bag, "b", t="0", m=str(len(player.inventory.items)))
		ET.SubElement(bag, "b", t="5", m=str(len(player.inventory.models)))

		items = ET.SubElement(inv, "items")

		in_0 = ET.SubElement(items, "in", t="0")
		items_ = [i for i in player.inventory.items if i is not None]
		for item in items_:
			ET.SubElement(in_0, "i", l=str(item.lot), c=str(item.amount), id=str(item.object_id), s=str(player.inventory.items.index(item)))

		in_2 = ET.SubElement(items, "in", t="2")
		for brick in player.inventory.bricks:
			ET.SubElement(in_2, "i", l=str(brick.lot), c=str(brick.amount), id=str(brick.object_id), s=str(player.inventory.bricks.index(brick)))

		in_5 = ET.SubElement(items, "in", t="5")
		models = [i for i in player.inventory.models if i is not None]
		for model in models:
			i = ET.SubElement(in_5, "i", l=str(model.lot), c=str(model.amount), id=str(model.object_id), s=str(player.inventory.models.index(model)))
			if hasattr(model, "module_lots"):
				module_lots = [(LDFDataType.INT32, i) for i in model.module_lots]
				module_lots = LDF().to_str_type(LDFDataType.STRING, module_lots)
				ET.SubElement(i, "x", ma=module_lots)

		flag = ET.SubElement(root, "flag")
		i = 0
		while True:
			# split the flags into 64 bit chunks
			chunk = player.char.flags >> (64*i)
			if not chunk:
				break
			chunk &= 0xffffffffffffffff
			ET.SubElement(flag, "f", id=str(i), v=str(chunk))
			i += 1

		mis = ET.SubElement(root, "mis")
		done = ET.SubElement(mis, "done")
		cur = ET.SubElement(mis, "cur")
		for mission_id, mission in player.char.missions.items():
			if mission.state == 2:
				m = ET.SubElement(cur, "m", id=str(mission_id))
				for task in mission.tasks:
					if task.value == 0:
						ET.SubElement(m, "sv")
					else:
						ET.SubElement(m, "sv", v=str(task.value))
						if task.type == TaskType.Collect:
							for collectible_id in task.parameter:
								ET.SubElement(m, "sv", v=str(collectible_id))
			elif mission.state == 8:
				ET.SubElement(done, "m", id=str(mission_id))

		import xml.dom.minidom
		xml = xml.dom.minidom.parseString((ET.tostring(root, encoding="unicode")))
		#log.debug(xml.toprettyxml(indent="  "))

		chd_ldf = LDF()
		chd_ldf.ldf_set("objid", LDFDataType.INT64_9, player.object_id)
		chd_ldf.ldf_set("template", LDFDataType.INT32, 1)
		chd_ldf.ldf_set("name", LDFDataType.STRING, player.name)
		chd_ldf.ldf_set("xmlData", LDFDataType.BYTES, ET.tostring(root))

		encoded_ldf = chd_ldf.to_bitstream()
		chardata.write(encoded_ldf)
		self.server.send(chardata, address)

		self.server.game_objects[player.object_id] = player
		self.server.add_participant(address) # Add to replica manager sync list
		self.server.construct(player)
		player.char.server_done_loading_all_objects()

	def on_position_update(self, message, address):
		player = self.server.accounts[address].characters.selected()
		vehicle = None
		if player.char.vehicle_id != 0:
			vehicle = self.server.game_objects[player.char.vehicle_id]
			serialize = player._serialize
		player.physics.position.update(message.read(c_float), message.read(c_float), message.read(c_float))
		player.physics.attr_changed("position")
		player.physics.rotation.update(message.read(c_float), message.read(c_float), message.read(c_float), message.read(c_float))
		player.physics.attr_changed("rotation")
		player.physics.on_ground = message.read(c_bit)
		player.physics.unknown_bool = message.read(c_bit)
		if player.physics.unknown_bool:
			print("is on rail?", player.physics.unknown_bool)
		if vehicle:
			vehicle.physics.position.update(player.physics.position)
			vehicle.physics.attr_changed("position")
			vehicle.physics.rotation.update(player.physics.rotation)
			vehicle.physics.attr_changed("rotation")
			vehicle.physics.on_ground = player.physics.on_ground
			vehicle.physics.unknown_bool = player.physics.unknown_bool
		if message.read(c_bit):
			player.physics.velocity.update(message.read(c_float), message.read(c_float), message.read(c_float))
			player.physics.attr_changed("velocity")
			if vehicle:
				vehicle.physics.velocity.update(player.physics.velocity)
				vehicle.physics.attr_changed("velocity")
		if message.read(c_bit):
			player.physics.angular_velocity = message.read(c_float), message.read(c_float), message.read(c_float)
			if vehicle:
				vehicle.physics.angular_velocity = player.physics.angular_velocity
		if message.read(c_bit):
			# apparently moving platform stuff
			player.physics.unknown_object_id = message.read(c_int64)
			player.physics.unknown_float3 = message.read(c_float), message.read(c_float), message.read(c_float)
			#print("unknown_object_id", player.physics.unknown_object_id, "unknown_float3", player.physics.unknown_float3)
			if vehicle:
				vehicle.physics.unknown_object_id = player.physics.unknown_object_id
				vehicle.physics.unknown_float3 = player.physics.unknown_float3
			if message.read(c_bit):
				player.physics.deeper_unknown_float3 = message.read(c_float), message.read(c_float), message.read(c_float)
				#print("deeper_unknown_float3", player.deeper_unknown_float3)
				if vehicle:
					vehicle.physics.deeper_unknown_float3 = player.physics.deeper_unknown_float3
		if vehicle:
			player._serialize = serialize

		# physics check for collisions
		if player.stats.life != 0:
			self.server.physics.check_collisions(player)

	def on_game_message(self, message, address):
		object_id = message.read(c_int64)
		obj = self.server.get_object(object_id)
		if obj is None:
			return

		message_id = message.read(c_ushort)
		try:
			message_name = GameMessage(message_id).name
		except ValueError:
			return
		handler_name = re.sub("(?!^)([A-Z])", r"_\1", message_name).lower()

		handlers = obj.handlers(handler_name)
		if not handlers:
			return

		signature = inspect.signature(handlers[0])
		kwargs = {}
		params = list(signature.parameters.values())
		if params and params[0].name == "player":
			params.pop(0)
		for param in params:
			if param.annotation == c_bit:
				value = message.read(c_bit)
				if param.default not in (param.empty, None) and value == param.default:
					continue
			else:
				if param.default not in (param.empty, None):
					is_not_default = message.read(c_bit)
					if not is_not_default:
						continue

				value = game_message_deserialize(message, param.annotation)

			kwargs[param.name] = value
		assert message.all_read()

		if message_name != "ReadyForUpdates": # todo: don't hardcode this
			if kwargs:
				log.debug(", ".join("%s=%s" % (key, value) for key, value in kwargs.items()))

		player = self.server.accounts[address].characters.selected()
		for handler in handlers:
			if hasattr(handler, "__wrapped__"):
				handler = functools.partial(handler.__wrapped__, handler.__self__)
			signature = inspect.signature(handler)
			if "player" in signature.parameters:
				handler(player, **kwargs)
			else:
				handler(**kwargs)
