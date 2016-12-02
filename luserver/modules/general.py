"""
For world server packet handling that is general enough not to be grouped in a specialized handling module.
"""
import logging
import xml.etree.ElementTree as ET

from .. import ldf
from ..bitstream import BitStream, c_bit, c_float, c_int, c_int64, c_uint, c_ushort
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
		char_= ET.SubElement(root, "char", cc=str(player.char.currency))
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
				module_lots = [(c_int, i) for i in model.module_lots]
				module_lots = ldf.to_ldf((str, module_lots), ldf_type="text")
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
		for mission in player.char.missions:
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

		chd_ldf = {}
		chd_ldf["objid"] = c_int64, player.object_id
		chd_ldf["template"] = c_int, 1
		chd_ldf["name"] = str, player.name
		chd_ldf["xmlData"] = bytes, ET.tostring(root)

		encoded_ldf = ldf.to_ldf(chd_ldf, ldf_type="binary")
		chardata.write(encoded_ldf)
		self.server.send(chardata, address)

		self.server.game_objects[player.object_id] = player
		self.server.add_participant(address) # Add to replica manager sync list
		self.server.construct(player)
		self.server.send_game_message(player.char.server_done_loading_all_objects, address=address)
		self.server.send_game_message(player.char.player_ready, address=address)
		self.server.send_game_message(player.char.restore_to_post_load_stats, address=address)
		for inv in (player.inventory.items, player.inventory.temp_items, player.inventory.models):
			for item in inv:
				if item is not None and item.equipped:
					player.skill.add_skill_for_item(item, add_buffs=False)
		if self.server.world_control_object is not None and hasattr(self.server.world_control_object.script, "player_ready"):
			self.server.send_game_message(self.server.world_control_object.script.player_ready, address=address)

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
		if not obj:
			return
		self.server.read_game_message(obj, message, address)
