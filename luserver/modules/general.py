"""
For world server packet handling that is general enough not to be grouped in a specialized handling module.
"""
import asyncio
import functools
import inspect
import logging
import re
import xml.etree.ElementTree as ET

from ..auth import GMLevel
from ..bitstream import BitStream, c_bit, c_float, c_int64, c_uint, c_ushort
from ..ldf import LDF, LDFDataType
from ..messages import GameMessage, WorldClientMsg, WorldServerMsg, game_message_deserialize
from ..world import server, World
from ..components.mission import TaskType

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
	World.AGPropLarge: 0x30e00e0,
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
	World.FVSiege: 0x6a801aa,
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

class GeneralHandling:
	def __init__(self):
		server.general = self
		self.tracked_objects = {}
		physics_debug_cmd = server.chat.commands.add_parser("physicsdebug")
		physics_debug_cmd.set_defaults(func=self.physics_debug_cmd)

		server.register_handler(WorldServerMsg.LoadComplete, self.on_client_load_complete)
		server.register_handler(WorldServerMsg.PositionUpdate, self.on_position_update)
		server.register_handler(WorldServerMsg.GameMessage, self.on_game_message)

	def physics_debug_cmd(self, args, sender):
		debug_markers = server.get_objects_in_group("physics_debug_marker")
		if not debug_markers:
			for obj in self.tracked_objects.copy():
				obj.physics.spawn_debug_marker()
		else:
			for marker in debug_markers:
				server.replica_manager.destruct(marker)

	def on_validated(self, address):
		player = server.accounts[address].characters.selected()
		if server.world_id[0] != 0:
			player.char.address = address
			server.game_objects[player.object_id] = player
			player.parent = None
			player.children = []
			player.parent_flag = False
			player.children_flag = False
			if player.char.account.gm_level != GMLevel.Admin and server.db.config["enabled_worlds"] and server.world_id[0] not in server.db.config["enabled_worlds"]:
				if player.char.world[0] != server.world_id[0]:
					dest = player.char.world
				else:
					dest = 1100, 0, 0
				asyncio.ensure_future(player.char.transfer_to_world(dest, respawn_point_name=""))
			else:
				self.send_load_world(server.world_id, address)

	def send_load_world(self, destination, address):
		world_id, world_instance, world_clone = destination
		player = server.accounts[address].characters.selected()

		load_world = BitStream()
		load_world.write_header(WorldClientMsg.LoadWorld)
		load_world.write(c_ushort(world_id))
		load_world.write(c_ushort(world_instance))
		load_world.write(c_uint(world_clone))
		load_world.write(c_uint(checksum.get(World(world_id), 0)))
		load_world.write(bytes(2))
		load_world.write(c_float(player.physics.position.x))
		load_world.write(c_float(player.physics.position.y))
		load_world.write(c_float(player.physics.position.z))
		load_world.write(bytes(4))
		server.send(load_world, address)

	def on_client_load_complete(self, data, address):
		player = server.accounts[address].characters.selected()

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
		ET.SubElement(bag, "b", t="7", m=str(len(player.inventory.behaviors)))

		items = ET.SubElement(inv, "items")

		in_0 = ET.SubElement(items, "in", t="0")
		for index, item in enumerate(player.inventory.items):
			if item is not None:
				optional = {}
				if item.count != 1:
					optional["c"] = str(item.count)
				ET.SubElement(in_0, "i", l=str(item.lot), id=str(item.object_id), s=str(index), **optional)

		in_2 = ET.SubElement(items, "in", t="2")
		for index, brick in enumerate(player.inventory.bricks):
			optional = {}
			if brick.count != 1:
				optional["c"] = str(brick.count)
			ET.SubElement(in_2, "i", l=str(brick.lot), id=str(brick.object_id), s=str(index), **optional)

		in_5 = ET.SubElement(items, "in", t="5")
		for index, model in enumerate(player.inventory.models):
			if model is not None:
				optional = {}
				if model.count != 1:
					optional["c"] = str(model.count)
				i = ET.SubElement(in_5, "i", l=str(model.lot), id=str(model.object_id), s=str(index), **optional)
				if hasattr(model, "module_lots"):
					module_lots = [(LDFDataType.INT32, i) for i in model.module_lots]
					module_lots = LDF().to_str_type(LDFDataType.STRING, module_lots)
					ET.SubElement(i, "x", ma=module_lots)

		in_7 = ET.SubElement(items, "in", t="7")
		for index, behavior in enumerate(player.inventory.behaviors):
			if behavior is not None:
				optional = {}
				if behavior.count != 1:
					optional["c"] = str(behavior.count)
				ET.SubElement(in_7, "i", l=str(behavior.lot), id=str(behavior.object_id), s=str(index), **optional)

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
		server.send(chardata, address)

		server.replica_manager.add_participant(address)  # Add to replica manager sync list
		server.replica_manager.construct(player)
		player.char.server_done_loading_all_objects()

	def on_position_update(self, message, address):
		player = server.accounts[address].characters.selected()
		vehicle = None
		if player.char.vehicle_id != 0:
			vehicle = server.game_objects[player.char.vehicle_id]
			serialized = player._serialize_scheduled
			player._serialize_scheduled = True
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
			player._serialize_scheduled = serialized

		if player.stats.life != 0:
			self.check_collisions(player)

	def check_collisions(self, player):
		collisions = []
		for obj, coll in self.tracked_objects.items():
			if coll.is_point_within(player.physics.position):
				collisions.append(obj.object_id)

		for object_id in collisions:
			if object_id not in player.char.last_collisions:
				server.get_object(object_id).handle("on_enter", player)
		for object_id in player.char.last_collisions:
			if object_id not in collisions:
				obj = server.get_object(object_id)
				if obj is not None:
					obj.handle("on_exit", player, silent=True)

		player.char.last_collisions = collisions

	def on_game_message(self, message, address):
		object_id = message.read(c_int64)
		obj = server.get_object(object_id)
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
		if params and params[0].name == "player" and params[0].annotation == inspect.Parameter.empty and params[0].default == inspect.Parameter.empty:
			params.pop(0)
		for param in params:
			if param.annotation == bool:
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

		player = server.accounts[address].characters.selected()
		for handler in handlers:
			if hasattr(handler, "__wrapped__"):
				handler = functools.partial(handler.__wrapped__, handler.__self__)
			signature = inspect.signature(handler)
			playerarg = "player" in signature.parameters
			if playerarg:
				it = iter(signature.parameters.keys())
				playerarg = next(it) == "player"
				if playerarg:
					arg = signature.parameters["player"]
					playerarg = arg.annotation == inspect.Parameter.empty and arg.default == inspect.Parameter.empty
			if playerarg:
				handler(player, **kwargs)
			else:
				handler(**kwargs)
