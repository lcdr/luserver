"""
For world server packet handling that is general enough not to be grouped in a specialized handling module.
"""
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import cast, Dict, Tuple

from bitstream import c_bit, c_float, c_int64, c_uint, c_ushort, ReadStream
from pyraknet.transports.abc import Connection
from ..auth import GMLevel
from ..bitstream import WriteStream
from ..game_object import ControllableObject, GameObject, Player
from ..ldf import LDF, LDFDataType
from ..messages import WorldClientMsg, WorldServerMsg
from ..world import server, World
from ..components.mission import TaskType
from ..components.physics import Collider

log = logging.getLogger(__name__)

# Constant checksums that the client expects to verify map version
# (likely value of the last map revision)
_CHECKSUMS = {
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
	def __init__(self) -> None:
		self.tracked_objects: Dict[GameObject, Collider] = {}

		server._dispatcher.add_listener(WorldServerMsg.LoadComplete, self._on_client_load_complete)
		server._dispatcher.add_listener(WorldServerMsg.PositionUpdate, self._on_position_update)
		server._dispatcher.add_listener(WorldServerMsg.GameMessage, self._on_game_message)

	def on_validated(self, conn: Connection) -> None:
		if server.world_id[0] != 0:
			player = server.accounts[conn].selected_char()
			server.player_data[player] = {"conn": conn}
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
				self._send_load_world(server.world_id, conn)

	def _send_load_world(self, destination: Tuple[int, int, int], conn: Connection) -> None:
		world_id, world_instance, world_clone = destination
		player = server.accounts[conn].selected_char()

		load_world = WriteStream()
		load_world.write_header(WorldClientMsg.LoadWorld)
		load_world.write(c_ushort(world_id))
		load_world.write(c_ushort(world_instance))
		load_world.write(c_uint(world_clone))
		load_world.write(c_uint(_CHECKSUMS.get(World(world_id), 0)))
		load_world.write(bytes(2))
		load_world.write(player.physics.position)
		load_world.write(bytes(4))
		conn.send(load_world)

	def _on_client_load_complete(self, data: ReadStream, conn: Connection) -> None:
		player = server.accounts[conn].selected_char()

		chardata = WriteStream()
		chardata.write_header(WorldClientMsg.CharacterData)

		root = ET.Element("obj")
		char = ET.SubElement(root, "char", cc=str(player.char.currency))
		unlocked_emotes = ET.SubElement(char, "ue")
		for emote_id in player.char.unlocked_emotes:
			ET.SubElement(unlocked_emotes, "e", id=str(emote_id))
		inv = ET.SubElement(root, "inv")
		if player.inventory.consumable_slot_lot != -1:
			inv.set("csl", str(player.inventory.consumable_slot_lot))
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
				ET.SubElement(in_0, "i", optional, l=str(item.lot), id=str(item.object_id), s=str(index))

		in_2 = ET.SubElement(items, "in", t="2")
		for index, brick in enumerate(player.inventory.bricks):
			optional = {}
			if brick.count != 1:
				optional["c"] = str(brick.count)
			ET.SubElement(in_2, "i", optional, l=str(brick.lot), id=str(brick.object_id), s=str(index))

		in_5 = ET.SubElement(items, "in", t="5")
		for index, model in enumerate(player.inventory.models):
			if model is not None:
				optional = {}
				if model.count != 1:
					optional["c"] = str(model.count)
				i = ET.SubElement(in_5, "i", optional, l=str(model.lot), id=str(model.object_id), s=str(index))
				if hasattr(model, "module_lots"):
					module_lots = [(LDFDataType.INT32, i) for i in model.module_lots]
					ET.SubElement(i, "x", ma=LDF().to_str_type(LDFDataType.STRING, module_lots))

		in_7 = ET.SubElement(items, "in", t="7")
		for index, behavior in enumerate(player.inventory.behaviors):
			if behavior is not None:
				optional = {}
				if behavior.count != 1:
					optional["c"] = str(behavior.count)
				ET.SubElement(in_7, "i", optional, l=str(behavior.lot), id=str(behavior.object_id), s=str(index))

		flag = ET.SubElement(root, "flag")
		j = 0
		while True:
			# split the flags into 64 bit chunks
			chunk = player.char.flags >> (64*j)
			if not chunk:
				break
			chunk &= 0xffffffffffffffff
			ET.SubElement(flag, "f", id=str(j), v=str(chunk))
			j += 1

		mis = ET.SubElement(root, "mis")
		done = ET.SubElement(mis, "done")
		cur = ET.SubElement(mis, "cur")
		for mission_id, mission in player.char.mission.missions.items():
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

		#import xml.dom.minidom
		#xml = xml.dom.minidom.parseString((ET.tostring(root, encoding="unicode")))
		#log.debug(xml.toprettyxml(indent="  "))

		chd_ldf = LDF()
		chd_ldf.ldf_set("objid", LDFDataType.INT64_9, player.object_id)
		chd_ldf.ldf_set("template", LDFDataType.INT32, 1)
		chd_ldf.ldf_set("name", LDFDataType.STRING, player.name)
		chd_ldf.ldf_set("xmlData", LDFDataType.BYTES, ET.tostring(root))

		encoded_ldf = chd_ldf.to_bytes()
		chardata.write(encoded_ldf)
		conn.send(chardata)

		server.replica_manager.add_participant(conn)  # Add to replica manager sync list
		server.replica_manager.construct(player)
		player.char.server_done_loading_all_objects()

	def _on_position_update(self, message: ReadStream, conn: Connection) -> None:
		player = server.accounts[conn].selected_char()
		vehicle = None
		if player.char.vehicle_id != 0:
			vehicle = cast(ControllableObject, server.game_objects[player.char.vehicle_id])
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
			self._check_collisions(player)

	def _check_collisions(self, player: Player) -> None:
		collisions = []
		for obj, coll in self.tracked_objects.items():
			if coll.is_point_within(player.physics.position):
				collisions.append(obj.object_id)

		for object_id in collisions:
			if object_id not in player.char.last_collisions:
				server.get_object(object_id).handle("enter", player)
		for object_id in player.char.last_collisions:
			if object_id in server.game_objects and object_id not in collisions:
				obj = server.get_object(object_id)
				obj.handle("exit", player, silent=True)

		player.char.last_collisions = collisions

	def _on_game_message(self, message: ReadStream, conn: Connection) -> None:
		object_id = message.read(c_int64)
		try:
			obj = server.get_object(object_id)
		except KeyError:
			return
		obj.on_game_message(message, conn)
