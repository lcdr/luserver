import os
import xml.etree.ElementTree
from types import SimpleNamespace

import BTrees

import luserver.world
from luserver.bitstream import c_bool, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, ReadStream
from luserver.game_object import GameObject
from luserver.ldf import LDF
from luserver.world import World
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3
from lvl_importer import LVLImporter, parse_config

def import_data(root, maps_path):
	luserver.world._server = SimpleNamespace(db=root)
	luz_paths = {
		World.VentureExplorer: "01_live_maps/space_ship/nd_space_ship.luz",
		World.ReturnToTheVentureExplorer: "01_live_maps/space_ship/battle_instance/nd_space_ship_battle_instance.luz",
		World.AvantGardens: "01_live_maps/avant_gardens/nd_avant_gardens.luz",
		World.AvantGardensSurvival: "01_live_maps/avant_gardens/survival/nd_ag_survival_battlefield.luz",
		World.SpiderQueenBattle: "01_live_maps/avant_gardens/property/small/nd_ag_property_small.luz",
		World.BlockYard: "01_live_maps/avant_gardens/property/small/nd_ag_property_small.luz",
		World.AvantGrove: "01_live_maps/avant_gardens/property/medium/nd_ag_property_medium.luz",
		World.AGPropLarge: "2011_live_maps/pp_ag_large/nd_ag_property_large.luz",
		World.NimbusStation: "01_live_maps/nimbus_station/nd_nimbus_station.luz",
		World.PetCove: "01_live_maps/nimbus_station/pet_ranch/nd_ns_pet_ranch.luz",
		World.VertigoLoop: "01_live_maps/nimbus_station/racetrack/nd_nimbus_station_racetrack.luz",
		World.TheBattleOfNimbusStation: "01_live_maps/nimbus_station/waves/nd_ns_waves.luz",
		World.NimbusRock: "01_live_maps/nimbus_station/property/small/nd_ns_property_small.luz",
		World.NimbusIsle: "nsmed/nd_ns_property_medium.luz",
		World.GnarledForest: "01_live_maps/gnarled_forest/nd_gnarled_forest.luz",
		World.CannonCoveShootingGallery: "01_live_maps/gnarled_forest/shooting_gallery/nd_gf_sg_ships.luz",
		World.ChanteyShanty: "01_live_maps/gnarled_forest/property/small/nd_gf_property_small.luz",
		World.ForbiddenValley: "01_live_maps/forbidden_valley/nd_forbidden_valley.luz",
		World.FVSiege: "01_live_maps/forbidden_valley/siege/nd_fv_siege.luz",
		World.ForbiddenValleyDragonBattle: "01_live_maps/forbidden_valley/dragon_battle/nd_fv_dragon_crevice.luz",
		World.DragonmawChasm: "fvracetrack/fv_racetrack.luz",
		World.RavenBluff: "01_live_maps/forbidden_valley/property/small/nd_fv_property_small.luz",
		World.Starbase3001: "01_live_maps/lup_station/nd_starbase3001.luz",
		World.DeepFreeze: "01_live_maps/wbl/deep_freeze_intro/wbl_deep_freeze_intro.luz",
		World.RobotCity: "01_live_maps/wbl/robot_city_intro/wbl_robot_city_intro.luz",
		World.MoonBase: "01_live_maps/wbl/moon_base_intro/wbl_moon_base_intro.luz",
		World.Portabello: "01_live_maps/wbl/portabello/wbl_portabello.luz",
		World.LEGOClub: "01_live_maps/lego_club/nd_lego_club.luz",
		World.CruxPrime: "2011_live_maps/aura_mar/nd_aura_mar.luz",
		World.NexusTower: "nexustower/nd_nexus_tower.luz",
		World.NinjagoMonastery: "njhub/nd_nj_monastery.luz",
		World.BattleAgainstFrakjaw: "njhub/cave_instance/monastery_cave_instance.luz",
	}

	root.world_data = BTrees.IOBTree.BTree()
	for world, luz_path in luz_paths.items():
		luz_path = os.path.join(maps_path, luz_path)
		if world == World.KeelhaulCanyon:
			continue
		root.world_data[world.value] = SimpleNamespace(objects=BTrees.OOBTree.BTree(), paths=BTrees.OOBTree.BTree(), spawnpoint=(Vector3(), Quaternion()))

		_LUZImporter(luz_path, root, root.world_data[world.value])

def _parse_lutriggers(lutriggers_path):
	event_names = {
		"OnActivated": "on_activated",
		"OnCreate": "on_startup",
		"OnDectivated": "on_deactivated",
		"OnEnter": "on_enter"}

	triggers = {}
	tree = xml.etree.ElementTree.parse(lutriggers_path)
	triggers_elem = tree.getroot()
	for trigger in triggers_elem:
		events = {}
		for event in trigger:
			if event.attrib["id"] not in event_names:
				continue
			commands = []
			for command in event:
				if "args" in command.attrib:
					args = command.attrib["args"].split(",")
				else:
					args = ()
				if "targetName" in command.attrib:
					target = command.attrib["target"], command.attrib["targetName"]
				else:
					target = command.attrib["target"]
				commands.append((command.attrib["id"], target, args))
			events[event_names[event.attrib["id"]]] = commands
		triggers[int(trigger.attrib["id"])] = events
	return triggers

class _LUZImporter:
	def __init__(self, luz_path, root, world_data):
		self.root = root
		self.world_data = world_data
		with open(luz_path, "rb") as file:
			self.luz = ReadStream(file.read())
		self.parse_luz(luz_path)

	def parse_luz(self, luz_path):
		version = self.luz.read(c_uint)
		assert version in (36, 38, 39, 40, 41), version
		self.luz.skip_read(4 + 4)
		if version >= 38:
			spawnpoint_position = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
			w, x, y, z = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
			self.world_data.spawnpoint = Vector3(*spawnpoint_position), Quaternion(x, y, z, w)

		if version >= 37:
			number_of_scenes = self.luz.read(c_uint)
		else:
			number_of_scenes = self.luz.read(c_ubyte)

		scenes = {}
		for _ in range(number_of_scenes):
			filename = self.luz.read(bytes, length_type=c_ubyte).decode("latin1")
			scene_id = self.luz.read(c_uint64)
			self.luz.read(bytes, length_type=c_ubyte)
			self.luz.read(bytes, length=3)
			scenes[scene_id] = filename

		triggers = {}
		for scene_id, filename in scenes.items():
			lutriggers_path = os.path.join(os.path.dirname(luz_path), os.path.splitext(filename)[0] + ".lutriggers")
			if os.path.exists(lutriggers_path):
				triggers[scene_id] = _parse_lutriggers(lutriggers_path)

		for scene_id, filename in scenes.items():
			LVLImporter(os.path.join(os.path.dirname(luz_path), filename), self.root, self.world_data, triggers)

		assert self.luz.read(c_ubyte) == 0

		# terrain
		filename = self.luz.read(bytes, length_type=c_ubyte)
		name = self.luz.read(bytes, length_type=c_ubyte)
		description = self.luz.read(bytes, length_type=c_ubyte)

		# unknown
		for _ in range(self.luz.read(c_uint)):
			for _ in range(2):
				self.luz.skip_read(20)

		remaining_length = self.luz.read(c_uint)
		assert len(self.luz) - self.luz.read_offset // 8 == remaining_length
		assert self.luz.read(c_uint) == 1

		self.parse_paths()

	def parse_paths(self):
		class PathType:
			Movement = 0
			MovingPlatform = 1
			Property = 2
			Camera = 3
			Spawner = 4
			Showcase = 5
			Race = 6
			Rail = 7

		for _ in range(self.luz.read(c_uint)):
			path_version = self.luz.read(c_uint)
			path_name = self.luz.read(str, length_type=c_ubyte)
			path_type = self.luz.read(c_uint)
			unknown1 = self.luz.read(c_uint)
			path_behavior = self.luz.read(c_uint)

			if path_type == PathType.MovingPlatform:
				if path_version >= 18:
					unknown3 = self.luz.skip_read(1)
				elif path_version >= 13:
					unknown_str = self.luz.read(str, length_type=c_ubyte)

			elif path_type == PathType.Property:
				self.luz.skip_read(20)
				unknown_str1 = self.luz.read(str, length_type=c_ubyte)
				unknown_str2 = self.luz.read(str, length_type=c_uint)
				self.luz.skip_read(36)

			elif path_type == PathType.Camera:
				unknown_str = self.luz.read(str, length_type=c_ubyte)
				if path_version >= 14:
					unknown3 = self.luz.skip_read(1)

			elif path_type == PathType.Spawner:
				spawner_vars = {
					"spawntemplate": self.luz.read(c_uint),
					"respawn_time": self.luz.read(c_uint)
				}
				max_to_spawn = self.luz.read(c_int)
				num_to_maintain = self.luz.read(c_uint)
				assert max_to_spawn == -1 or max_to_spawn == num_to_maintain
				spawner_vars["num_to_maintain"] = num_to_maintain
				object_id = self.luz.read(c_int64)
				spawner_vars["active_on_load"] = self.luz.read(c_bool)

			waypoints = []

			for _ in range(self.luz.read(c_uint)):
				position = Vector3(self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float))

				if path_type == PathType.MovingPlatform:
					rotation = Quaternion(self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float))
					waypoint_unknown2 = self.luz.read(c_ubyte)
					speed = self.luz.read(c_float)
					wait = self.luz.read(c_float)

					if path_version >= 13:
						waypoint_audio_guid_1 = self.luz.read(str, length_type=c_ubyte)
						waypoint_audio_guid_2 = self.luz.read(str, length_type=c_ubyte)

				elif path_type == PathType.Camera:
					self.luz.skip_read(36)

				elif path_type == PathType.Spawner:
					w, x, y, z = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
					rotation = Quaternion(x, y, z, w)

				elif path_type == PathType.Race:
					self.luz.skip_read(30)

				elif path_type == PathType.Rail:
					self.luz.skip_read(16)
					if path_version >= 17:
						self.luz.skip_read(4)

				if path_type in (PathType.Movement, PathType.Spawner, PathType.Rail):
					config = LDF()
					for _ in range(self.luz.read(c_uint)):
						config_name = self.luz.read(str, length_type=c_ubyte)
						config_type_and_value = self.luz.read(str, length_type=c_ubyte)
						try:
							config.ldf_set(config_name, *LDF.from_str_type(config_type_and_value))
						except ValueError:
							pass

				if path_type == PathType.MovingPlatform:
					waypoints.append((position, speed, wait))
				elif path_type == PathType.Spawner:
					spawned_vars = {"position": position, "rotation": rotation}
					spawned_vars.update(parse_config(config))
					waypoints.append(spawned_vars)

			waypoints = tuple(waypoints)
			if path_type == PathType.MovingPlatform:
				self.world_data.paths[path_name] = path_behavior, waypoints
			elif path_type == PathType.Spawner:
				if spawner_vars["spawntemplate"] == 0:
					continue
				spawner_vars["spawner_name"] = path_name
				spawner_vars["spawner_waypoints"] = waypoints
				spawner = GameObject(176, object_id, spawner_vars)
				self.world_data.objects[object_id] = spawner
