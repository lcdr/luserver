import os
import xml.etree.ElementTree
from types import SimpleNamespace

import BTrees

import luserver.world
from luserver.bitstream import BitStream, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from luserver.game_object import GameObject
from luserver.ldf import LDF
from luserver.world import BITS_LOCAL, World
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3
import scripts

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

def _parse_config(config, triggers=None):
	spawned_vars = {}

	if "custom_script_client" in config:
		spawned_vars["custom_script"] = None
	if "custom_script_server" in config:
		if config["custom_script_server"] == "":
			spawned_vars["custom_script"] = None
		else:
			spawned_vars["custom_script"] = scripts.SCRIPTS.get(config["custom_script_server"][len("scripts\\"):])
	if "groupID" in config:
		spawned_vars["groups"] = config["groupID"][:-1].split(";")
	if "is_smashable" in config:
		spawned_vars["is_smashable"] = config["is_smashable"]
	if "markedAsPhantom" in config:
		spawned_vars["marked_as_phantom"] = True
	if "primitiveModelType" in config:
		spawned_vars["primitive_model_type"] = config["primitiveModelType"]
		primitive_model_scale = Vector3(config["primitiveModelValueX"], config["primitiveModelValueY"], config["primitiveModelValueZ"])
		spawned_vars["primitive_model_scale"] = primitive_model_scale
	if "renderDisabled" in config:
		spawned_vars["render_disabled"] = True
	if "respawnname" in config:
		spawned_vars["respawn_name"] = config["respawnname"]
	if "respawnVol" in config and config["respawnVol"]:
		spawned_vars["respawn_data"] = Vector3([float(i) for i in config["rspPos"].split("\x1f")]), Quaternion([float(i) for i in config["rspRot"].split("\x1f")])
	if "targetScene" in config:
		spawned_vars["respawn_point_name"] = config["targetScene"]
	if "transferZoneID" in config:
		spawned_vars["transfer_world_id"] = int(config["transferZoneID"])
	if "trigger_id" in config and triggers is not None:
		trigger_scene_id, trigger_id = (int(i) for i in config["trigger_id"].split(":"))
		if trigger_scene_id in triggers and trigger_id in triggers[trigger_scene_id]:
			spawned_vars["trigger_events"] = triggers[trigger_scene_id][trigger_id]

	script_vars = {}
	spawned_vars["script_vars"] = script_vars

	if "altFlagID" in config:
		script_vars["alt_flag_id"] = config["altFlagID"]
	if "Cinematic" in config:
		script_vars["cinematic"] = config["Cinematic"]
	if "ForceAmt" in config:
		script_vars["force_amount"] = config["ForceAmt"]
	if "ForceX" in config and "ForceY" in config and "ForceX" in config:
		script_vars["force"] = Vector3(config["ForceX"], config["ForceY"], config["ForceZ"])
	if "FrictionAmt" in config:
		script_vars["friction_amount"] = config["FrictionAmt"]
	if "number" in config:
		script_vars["flag_id"] = int(config["number"])
	if "POI" in config:
		script_vars["poi"] = config["POI"]
	if "storyText" in config:
		script_vars["flag_id"] = int(config["storyText"][-2:])
	if "teleGroup" in config:
		script_vars["teleport_respawn_point_name"] = config["teleGroup"]
	if "TouchCompleteID" in config:
		script_vars["touch_complete_mission_id"] = config["TouchCompleteID"]
	if "transferText" in config:
		script_vars["transfer_text"] = config["transferText"]
	if "transferZoneID" in config:
		script_vars["transfer_world_id"] = int(config["transferZoneID"])
	if "volGroup" in config:
		script_vars["volume_group"] = config["volGroup"]

	return spawned_vars

class _LUZImporter:
	def __init__(self, luz_path, root, world_data):
		self.root = root
		self.world_data = world_data
		with open(luz_path, "rb") as file:
			self.luz = BitStream(file.read())
		self.parse_luz(luz_path)

	def parse_luz(self, luz_path):
		version = self.luz.read(c_uint)
		assert version in (36, 38, 39, 40, 41), version
		self.luz.skip_read(4 + 4)
		if version >= 38:
			spawnpoint_position = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
			w, x, y, z = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
			self.world_data.spawnpoint = Vector3(spawnpoint_position), Quaternion(x, y, z, w)

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
			_LVLImporter(os.path.join(os.path.dirname(luz_path), filename), self.root, self.world_data, triggers)

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
		assert len(self.luz) - self.luz._read_offset // 8 == remaining_length
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
					"spawner_unknown": (self.luz.read(c_uint), self.luz.read(c_int), self.luz.read(c_uint))}
				object_id = self.luz.read(c_int64)
				unknown3 = self.luz.read(c_ubyte)

			waypoints = []

			for _ in range(self.luz.read(c_uint)):
				position = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)

				if path_type == PathType.MovingPlatform:
					rotation = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
					waypoint_unknown2 = self.luz.read(c_ubyte)
					waypoint_unknown3 = self.luz.read(c_float)
					waypoint_unknown4 = self.luz.read(c_float)

					if path_version >= 13:
						waypoint_audio_guid_1 = self.luz.read(str, length_type=c_ubyte)
						waypoint_audio_guid_2 = self.luz.read(str, length_type=c_ubyte)

				elif path_type == PathType.Camera:
					self.luz.skip_read(36)

				elif path_type == PathType.Spawner:
					w, x, y, z = self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float), self.luz.read(c_float)
					rotation = x, y, z, w

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
					waypoints.append((position, waypoint_unknown3, waypoint_unknown4))
				elif path_type == PathType.Spawner:
					spawned_vars = {"position": position, "rotation": rotation}
					spawned_vars.update(_parse_config(config))
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

class _LVLImporter:
	def __init__(self, lvl_path, root, world_data, triggers):
		self.root = root
		self.world_data = world_data
		self.triggers = triggers
		with open(lvl_path, "rb") as file:
			self.lvl = BitStream(file.read())

		self.parse_lvl()

	def parse_lvl(self):
		if self.lvl[0:4] == b"CHNK":
			while True:
				if self.lvl._read_offset // 8 == len(self.lvl):  # end of file
					break
				assert self.lvl._read_offset // 8 % 16 == 0  # seems everything is aligned like this?
				start_pos = self.lvl._read_offset // 8
				assert self.lvl.read(bytes, length=4) == b"CHNK"
				chunktype = self.lvl.read(c_uint)
				assert self.lvl.read(c_ushort) == 1
				assert self.lvl.read(c_ushort) in (1, 2)
				chunk_length = self.lvl.read(c_uint)  # position of next CHNK relative to this CHNK
				data_pos = self.lvl.read(c_uint)
				self.lvl._read_offset = data_pos * 8
				assert self.lvl._read_offset // 8 % 16 == 0
				if chunktype == 2001:
					self.parse_chunk_type_2001()
				self.lvl._read_offset = (start_pos + chunk_length) * 8  # go to the next CHNK
		else:
			self.parse_old_lvl_header()
			self.parse_chunk_type_2001()

	def parse_old_lvl_header(self):
		version = self.lvl.read(c_ushort)
		assert self.lvl.read(c_ushort) == version
		self.lvl.read(c_ubyte)
		self.lvl.read(c_uint)
		if version >= 45:
			self.lvl.read(c_float)
		for _ in range(4*3):
			self.lvl.read(c_float)
		if version >= 31:
			if version >= 39:
				for _ in range(12):
					self.lvl.read(c_float)
				if version >= 40:
					for _ in range(self.lvl.read(c_uint)):
						self.lvl.read(c_uint)
						self.lvl.read(c_float)
						self.lvl.read(c_float)
			else:
				self.lvl.read(c_float)
				self.lvl.read(c_float)

			for _ in range(3):
				self.lvl.read(c_float)

		if version >= 36:
			for _ in range(3):
				self.lvl.read(c_float)

		if version < 42:
			for _ in range(3):
				self.lvl.read(c_float)
			if version >= 33:
				for _ in range(4):
					self.lvl.read(c_float)

		self.lvl.read(bytes, length_type=c_uint)
		for _ in range(5):
			self.lvl.read(bytes, length_type=c_uint)
		self.lvl.skip_read(4)
		for _ in range(self.lvl.read(c_uint)):
			self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float)

	def parse_chunk_type_2001(self):
		whitelisted_serverside_lots = 176, 2292, 3964, 4734, 4764, 4860, 4945, 5633, 5652, 6247, 6383, 6396, 6464, 6465, 6466, 6700, 6842, 6958, 6960, 7085, 7608, 7869, 7973, 8139, 8419, 9930, 10009, 10042, 10413, 10496, 11165, 11178, 11182, 11274, 11279, 11280, 11281, 12166, 12175, 12232, 12384, 12661, 13054, 13142, 13834, 13835, 13881, 13882, 14013, 14031, 14086, 14087, 14199, 14214, 14215, 14216, 14217, 14218, 14220, 14225, 14226, 14242, 14243, 14244, 14245, 14246, 14248, 14249, 14289, 14290, 14291, 14292, 14293, 14294, 14330, 14331, 14332, 14333, 14345, 14346, 14347, 14348, 14510, 14530, 15902, 16477, 16506, 16513, 16627

		for _ in range(self.lvl.read(c_uint)):
			object_id = self.lvl.read(c_int64)  # seems like the object id, but without some bits
			lot = self.lvl.read(c_uint)
			unknown1 = self.lvl.read(c_uint)
			unknown2 = self.lvl.read(c_uint)
			position = self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float)
			w, x, y, z = self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float)
			rotation = x, y, z, w
			scale = self.lvl.read(c_float)
			config_data = self.lvl.read(str, length_type=c_uint)
			assert self.lvl.read(c_uint) == 0

			object_id |= BITS_LOCAL
			if lot in whitelisted_serverside_lots:
				config = LDF(config_data)
				spawned_vars = {
					"scale": scale,
					"position": position,
					"rotation": rotation}
				spawned_vars.update(_parse_config(config, self.triggers))

				if lot == 176:
					if "activityID" in config:
						spawned_vars["activity_id"] = config["activityID"]
					if "attached_path" in config:
						spawned_vars["attached_path"] = config["attached_path"]
					if "collectible_id" in config:
						spawned_vars["collectible_id"] = config["collectible_id"]
					if "rebuild_activators" in config:
						spawned_vars["rebuild_activator_position"] = Vector3(
							*(float(i) for i in config["rebuild_activators"].split("\x1f")))
					if "rail_path" in config:
						spawned_vars["rail_path"] = config["rail_path"]
						spawned_vars["rail_path_start"] = config["rail_path_start"]

					if "KeyNum" in config:
						spawned_vars["script_vars"]["key_lot"] = config["KeyNum"]
					if "openItemID" in config:
						spawned_vars["script_vars"]["package_lot"] = config["openItemID"]

					spawner_vars = {}
					spawner_vars["spawntemplate"] = config["spawntemplate"]
					if "spawnsGroupOnSmash" in config:
						if config["spawnsGroupOnSmash"]:
							assert "spawnNetNameForSpawnGroupOnSmash" in config
							spawner_vars["spawn_net_on_smash"] = config["spawnNetNameForSpawnGroupOnSmash"]
					spawner_vars["spawner_waypoints"] = spawned_vars,
					spawned_vars = spawner_vars

				obj = GameObject(lot, object_id, spawned_vars)
				self.world_data.objects[object_id] = obj
