"""
For world server packet handling that is general enough not to be grouped in a specialized handling module.
"""
import logging
import xml.etree.ElementTree as ET

from .. import ldf
from ..bitstream import BitStream, c_bit, c_bool, c_float, c_int, c_int64, c_uint, c_ushort
from ..messages import WorldClientMsg, WorldServerMsg
from ..world import World
from .module import ServerModule

log = logging.getLogger(__name__)

# Constant checksums that the client expects to verify map version
# (likely value of the last map revision)
checksum = {}
checksum[World.VentureExplorer.value] = 0x20b8087c
checksum[World.ReturnToTheVentureExplorer.value] = 0x26680a3c
checksum[World.AvantGardens.value] = 0x49525511
checksum[World.AvantGardensSurvival.value] = 0x538214e2
checksum[World.SpiderQueenBattle.value] = 0xfd403da
checksum[World.BlockYard.value] = 0xfd403da
checksum[World.AvantGrove.value] = 0xa890303
checksum[World.NimbusStation.value] = 0xda1e6b30
checksum[World.PetCove.value] = 0x476e1330
checksum[World.VertigoLoop.value] = 0x10fc0502
checksum[World.TheBattleOfNimbusStation.value] = 0x7d40258
checksum[World.NimbusRock.value] = 0x58d0191
checksum[World.NimbusIsle.value] = 0x94f045d
checksum[World.GnarledForest.value] = 0x12eac290
checksum[World.CannonCoveShootingGallery.value] = 0xb7702ef
checksum[World.ChanteyShanty.value] = 0x4b6015c
checksum[World.ForbiddenValley.value] = 0x8519760d
checksum[World.ForbiddenValleyDragonBattle.value] = 0x2f50187
checksum[World.DragonmawChasm.value] = 0x81850f4e
checksum[World.RavenBluff.value] = 0x3f00126
checksum[World.Starbase3001.value] = 0x7c202ee
checksum[World.DeepFreeze.value] = 0x2320106
checksum[World.RobotCity.value] = 0x793037f
checksum[World.MoonBase.value] = 0x43b01ad
checksum[World.Portabello.value] = 0x181507dd
checksum[World.LEGOClub.value] = 0x2040138
checksum[World.CruxPrime.value] = 0x4b17a399
checksum[World.NexusTower.value] = 0x9e4af43c
checksum[World.NinjagoMonastery.value] = 0x4d692c74
checksum[World.BattleAgainstFrakjaw.value] = 0x9eb00ef

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
		load_world.write(c_uint(checksum[world_id]))
		load_world.write(bytes(2))
		load_world.write(c_float(player.position.x))
		load_world.write(c_float(player.position.y))
		load_world.write(c_float(player.position.z))
		load_world.write(bytes(4))
		self.server.send(load_world, address)

		player.world = destination

	def on_client_load_complete(self, data, address):
		char = self.server.accounts[address].characters.selected()

		chardata = BitStream()
		chardata.write_header(WorldClientMsg.CharacterData)

		root = ET.Element("obj")
		char_= ET.SubElement(root, "char", cc=str(char.currency))
		unlocked_emotes = ET.SubElement(char_, "ue")
		for emote_id in char.unlocked_emotes:
			ET.SubElement(unlocked_emotes, "e", id=str(emote_id))
		inv = ET.SubElement(root, "inv")
		bag = ET.SubElement(inv, "bag")
		ET.SubElement(bag, "b", t="0", m=str(len(char.items)))
		ET.SubElement(bag, "b", t="5", m=str(len(char.models)))

		items = ET.SubElement(inv, "items")

		in_0 = ET.SubElement(items, "in", t="0")
		items_ = [i for i in char.items if i is not None]
		for item in items_:
			ET.SubElement(in_0, "i", l=str(item.lot), c=str(item.amount), id=str(item.object_id), s=str(char.items.index(item)))

		in_2 = ET.SubElement(items, "in", t="2")
		for brick in char.bricks:
			ET.SubElement(in_2, "i", l=str(brick.lot), c=str(brick.amount), id=str(brick.object_id), s=str(char.bricks.index(brick)))

		in_5 = ET.SubElement(items, "in", t="5")
		models = [i for i in char.models if i is not None]
		for model in models:
			i = ET.SubElement(in_5, "i", l=str(model.lot), c=str(model.amount), id=str(model.object_id), s=str(char.models.index(model)))
			if hasattr(model, "module_lots"):
				module_lots = [(c_int, i) for i in model.module_lots]
				module_lots = ldf.to_ldf((str, module_lots), ldf_type="text")
				ET.SubElement(i, "x", ma=module_lots)

		flag = ET.SubElement(root, "flag")
		i = 0
		while True:
			# split the flags into 64 bit chunks
			chunk = char.flags >> (64*i)
			if not chunk:
				break
			chunk &= 0xffffffffffffffff
			ET.SubElement(flag, "f", id=str(i), v=str(chunk))
			i += 1

		mis = ET.SubElement(root, "mis")
		done = ET.SubElement(mis, "done")
		cur = ET.SubElement(mis, "cur")
		for mission in char.missions:
			if mission.state == 2:
				m = ET.SubElement(cur, "m", id=str(mission.id))
				for task in mission.tasks:
					if task.value == 0:
						ET.SubElement(m, "sv")
					else:
						ET.SubElement(m, "sv", v=str(task.value))
			elif mission.state == 8:
				ET.SubElement(done, "m", id=str(mission.id))

		import xml.dom.minidom
		xml = xml.dom.minidom.parseString((ET.tostring(root, encoding="unicode")))
		#log.debug(xml.toprettyxml(indent="  "))

		is_compressed = False

		chd_ldf = {}
		chd_ldf["objid"] = c_int64, char.object_id
		chd_ldf["template"] = c_int, 1
		chd_ldf["name"] = str, char.name
		chd_ldf["xmlData"] = bytes, ET.tostring(root)

		encoded_ldf = ldf.to_ldf(chd_ldf, ldf_type="binary")

		if not is_compressed:
			chardata.write(c_uint(len(encoded_ldf)+1))
		else:
			raise NotImplementedError
		chardata.write(c_bool(is_compressed))
		chardata.write(encoded_ldf)
		self.server.send(chardata, address)

		self.server.game_objects[char.object_id] = char
		self.server.add_participant(address) # Add to replica manager sync list
		self.server.construct(char)
		self.server.send_game_message(char.server_done_loading_all_objects, address=address)
		self.server.send_game_message(char.player_ready, address=address)
		self.server.send_game_message(char.restore_to_post_load_stats, address=address)
		for item in char.items:
			if item is not None and item.equipped:
				char.add_skill_for_item(item, add_buffs=False)

	def on_position_update(self, message, address):
		player = self.server.accounts[address].characters.selected()
		vehicle = None
		if player.vehicle_id != 0:
			vehicle = self.server.game_objects[player.vehicle_id]
			serialize = player._serialize
		player.position.update(message.read(c_float), message.read(c_float), message.read(c_float))
		player.attr_changed("position")
		player.rotation.update(message.read(c_float), message.read(c_float), message.read(c_float), message.read(c_float))
		player.attr_changed("rotation")
		player.on_ground = message.read(c_bit)
		player.unknown_bool = message.read(c_bit)
		if player.unknown_bool:
			print("is on rail?", player.unknown_bool)
		if vehicle:
			vehicle.position.update(player.position)
			vehicle.attr_changed("position")
			vehicle.rotation.update(player.rotation)
			vehicle.attr_changed("rotation")
			vehicle.on_ground = player.on_ground
			vehicle.unknown_bool = player.unknown_bool
		if message.read(c_bit):
			player.velocity.update(message.read(c_float), message.read(c_float), message.read(c_float))
			player.attr_changed("velocity")
			if vehicle:
				vehicle.velocity.update(player.velocity)
				vehicle.attr_changed("velocity")
		if message.read(c_bit):
			player.angular_velocity = message.read(c_float), message.read(c_float), message.read(c_float)
			if vehicle:
				vehicle.angular_velocity = player.angular_velocity
		if message.read(c_bit):
			# apparently moving platform stuff
			player.unknown_object_id = message.read(c_int64)
			player.unknown_float3 = message.read(c_float), message.read(c_float), message.read(c_float)
			#print("unknown_object_id", player.unknown_object_id, "unknown_float3", player.unknown_float3)
			if vehicle:
				vehicle.unknown_object_id = player.unknown_object_id
				vehicle.unknown_float3 = player.unknown_float3
			if message.read(c_bit):
				player.deeper_unknown_float3 = message.read(c_float), message.read(c_float), message.read(c_float)
				#print("deeper_unknown_float3", player.deeper_unknown_float3)
				if vehicle:
					vehicle.deeper_unknown_float3 = player.deeper_unknown_float3
		if vehicle:
			player._serialize = serialize

		# physics check for collisions
		if player.life != 0:
			self.server.physics.check_collisions(player)

	def on_game_message(self, message, address):
		object_id = message.read(c_int64)
		obj = self.server.get_object(object_id)
		if not obj:
			return
		self.server.read_game_message(obj, message, address)
