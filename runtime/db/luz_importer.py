import os
from types import SimpleNamespace

import BTrees

import luserver.ldf as ldf
from luserver.bitstream import BitStream, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from luserver.game_object_template import Template
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3
from luserver.world import BITS_LOCAL, World
import scripts

LUZ_PATHS = {}
LUZ_PATHS[World.VentureExplorer] = "01_live_maps/space_ship/nd_space_ship.luz"
LUZ_PATHS[World.ReturnToTheVentureExplorer] = "01_live_maps/space_ship/battle_instance/nd_space_ship_battle_instance.luz"
LUZ_PATHS[World.AvantGardens] = "01_live_maps/avant_gardens/nd_avant_gardens.luz"
LUZ_PATHS[World.AvantGardensSurvival] = "01_live_maps/avant_gardens/survival/nd_ag_survival_battlefield.luz"
LUZ_PATHS[World.SpiderQueenBattle] = "01_live_maps/avant_gardens/property/small/nd_ag_property_small.luz"
LUZ_PATHS[World.BlockYard] = "01_live_maps/avant_gardens/property/small/nd_ag_property_small.luz"
LUZ_PATHS[World.AvantGrove] = "01_live_maps/avant_gardens/property/medium/nd_ag_property_medium.luz"
LUZ_PATHS[World.NimbusStation] = "01_live_maps/nimbus_station/nd_nimbus_station.luz"
LUZ_PATHS[World.PetCove] = "01_live_maps/nimbus_station/pet_ranch/nd_ns_pet_ranch.luz"
LUZ_PATHS[World.VertigoLoop] = "01_live_maps/nimbus_station/racetrack/nd_nimbus_station_racetrack.luz"
LUZ_PATHS[World.TheBattleOfNimbusStation] = "01_live_maps/nimbus_station/waves/nd_ns_waves.luz"
LUZ_PATHS[World.NimbusRock] = "01_live_maps/nimbus_station/property/small/nd_ns_property_small.luz"
LUZ_PATHS[World.NimbusIsle] = "nsmed/nd_ns_property_medium.luz"
LUZ_PATHS[World.GnarledForest] = "01_live_maps/gnarled_forest/nd_gnarled_forest.luz"
LUZ_PATHS[World.CannonCoveShootingGallery] = "01_live_maps/gnarled_forest/shooting_gallery/nd_gf_sg_ships.luz"
LUZ_PATHS[World.ChanteyShanty] = "01_live_maps/gnarled_forest/property/small/nd_gf_property_small.luz"
LUZ_PATHS[World.ForbiddenValley] = "01_live_maps/forbidden_valley/nd_forbidden_valley.luz"
LUZ_PATHS[World.ForbiddenValleyDragonBattle] = "01_live_maps/forbidden_valley/dragon_battle/nd_fv_dragon_crevice.luz"
LUZ_PATHS[World.DragonmawChasm] = "fvracetrack/fv_racetrack.luz"
LUZ_PATHS[World.RavenBluff] = "01_live_maps/forbidden_valley/property/small/nd_fv_property_small.luz"
LUZ_PATHS[World.Starbase3001] = "01_live_maps/lup_station/nd_starbase3001.luz"
LUZ_PATHS[World.DeepFreeze] = "01_live_maps/wbl/deep_freeze_intro/wbl_deep_freeze_intro.luz"
LUZ_PATHS[World.RobotCity] = "01_live_maps/wbl/robot_city_intro/wbl_robot_city_intro.luz"
LUZ_PATHS[World.MoonBase] = "01_live_maps/wbl/moon_base_intro/wbl_moon_base_intro.luz"
LUZ_PATHS[World.Portabello] = "01_live_maps/wbl/portabello/wbl_portabello.luz"
LUZ_PATHS[World.LEGOClub] = "01_live_maps/lego_club/nd_lego_club.luz"
LUZ_PATHS[World.CruxPrime] = "2011_live_maps/aura_mar/nd_aura_mar.luz"
LUZ_PATHS[World.NexusTower] = "nexustower/nd_nexus_tower.luz"
LUZ_PATHS[World.NinjagoMonastery] = "njhub/nd_nj_monastery.luz"
LUZ_PATHS[World.BattleAgainstFrakjaw] = "njhub/cave_instance/monastery_cave_instance.luz"

class PathType:
	Movement  = 0
	MovingPlatform = 1
	Property = 2
	Camera = 3
	Spawner = 4
	Showcase = 5
	Race = 6
	Rail = 7

WHITELISTED_SERVERSIDE_LOTS = 176, 3964, 4734, 4764, 4860, 4945, 5633, 5652, 6247, 6396, 6700, 6842, 6958, 6960, 7085, 7608, 7973, 8139, 8419, 9930, 10009, 10042, 10413, 10496, 11165, 11178, 11274, 11279, 11280, 11281, 12232, 12661, 13834, 13835, 13881, 13882, 14013, 14031, 14086, 14087, 14199, 14214, 14215, 14216, 14217, 14218, 14220, 14226, 14242, 14243, 14244, 14245, 14246, 14248, 14249, 14289, 14290, 14291, 14292, 14293, 14294, 14330, 14331, 14332, 14333, 14347, 14348, 14510, 14530, 16513, 16627

def parse_lvl(conn, world_data, lvl_path):
	with open(lvl_path, "rb") as file:
		lvl = BitStream(file.read())

	while True:
		if lvl._read_offset//8 == len(lvl): # end of file
			break
		assert lvl._read_offset//8 % 16 == 0 # seems everything is aligned like this?
		start_pos = lvl._read_offset//8
		try:
			assert lvl.read(bytes, length=4) == b"CHNK"
		except AssertionError:
			print(lvl_path, "doesn't start with usual header")
			break
		chunktype = lvl.read(c_uint)
		assert lvl.read(c_ushort) == 1
		assert lvl.read(c_ushort) in (1, 2)
		chunk_length = lvl.read(c_uint) # position of next CHNK relative to this CHNK
		data_pos = lvl.read(c_uint)
		lvl._read_offset = data_pos * 8
		assert lvl._read_offset//8 % 16 == 0
		if chunktype == 2001:
			for _ in range(lvl.read(c_uint)):
				object_id = lvl.read(c_int64) # seems like the object id, but without some bits
				lot = lvl.read(c_uint)
				unknown1 = lvl.read(c_uint)
				unknown2 = lvl.read(c_uint)
				position = lvl.read(c_float), lvl.read(c_float), lvl.read(c_float)
				w, x, y, z = lvl.read(c_float), lvl.read(c_float), lvl.read(c_float), lvl.read(c_float)
				rotation = x, y, z, w
				scale = lvl.read(c_float)
				config_data = lvl.read(str, length_type=c_uint)
				assert lvl.read(c_uint) == 0

				object_id |= BITS_LOCAL
				if lot in WHITELISTED_SERVERSIDE_LOTS:
					config = ldf.from_ldf(config_data)

					custom_script = None
					if lot != 176 and "custom_script_server" in config:
						if config["custom_script_server"] == "":
							custom_script = ""
						else:
							custom_script = scripts.SCRIPTS.get(config["custom_script_server"][len("scripts\\"):])

					spawned_vars = {}
					if "groupID" in config:
						spawned_vars["groups"] = config["groupID"][:-1].split(";")
					if "respawnname" in config:
						spawned_vars["respawn_name"] = config["respawnname"]

					obj = Template(lot, conn, custom_script=custom_script)(object_id, SimpleNamespace(db=conn.root), set_vars=spawned_vars)
					if not hasattr(obj, "position"):
						obj.position = Vector3(*position)
					else:
						obj.position.update(*position)

					if not hasattr(obj, "rotation"):
						obj.rotation = Quaternion(*rotation)
					else:
						obj.rotation.update(*rotation)

					obj.scale = scale

					script_vars = {}

					if "altFlagID" in config:
						script_vars["alt_flag_id"] = config["altFlagID"]
					if "number" in config:
						script_vars["flag_id"] = int(config["number"])
					if "storyText" in config:
						script_vars["flag_id"] = int(config["storyText"][-2:])
					if "teleGroup" in config:
						script_vars["teleport_respawn_point_name"] = config["teleGroup"]
					if "TouchCompleteID" in config:
						script_vars["touch_complete_mission_id"] = config["TouchCompleteID"]
					if "transferZoneID" in config:
						script_vars["transfer_world_id"] = int(config["transferZoneID"])

					if lot == 176:
						spawn_vars = {}

						obj.spawntemplate = config["spawntemplate"]
						if "custom_script_server" in config:
							if config["custom_script_server"] == "":
								spawn_vars["custom_script"] = ""
							else:
								spawn_vars["custom_script"] = scripts.SCRIPTS.get(config["custom_script_server"][len("scripts\\"):])

						if "attached_path" in config:
							spawned_vars["attached_path"] = config["attached_path"]
						if "rebuild_activators" in config:
							spawned_vars["rebuild_activator_position"] = Vector3(*(float(i) for i in config["rebuild_activators"].split("\x1f")))
						if "rail_path" in config:
							spawned_vars["rail_path"] = config["rail_path"]
							spawned_vars["rail_path_start"] = config["rail_path_start"]

						if "KeyNum" in config:
							script_vars["key_lot"] = config["KeyNum"]
						if "openItemID" in config:
							script_vars["package_lot"] = config["openItemID"]

						obj.waypoints = (position, rotation, spawn_vars, spawned_vars, script_vars),
					else:
						obj.script_vars = script_vars

					del obj._v_server
					world_data.objects[object_id] = obj

		lvl._read_offset = (start_pos + chunk_length) * 8 # go to the next CHNK

def load_world_data(conn, maps_path):
	conn.root.world_data = BTrees.IOBTree.BTree()
	for world, luz_path in LUZ_PATHS.items():
		luz_path = maps_path + luz_path
		if world == World.KeelhaulCanyon:
			continue
		conn.root.world_data[world.value] = SimpleNamespace(objects=BTrees.OOBTree.BTree(), paths=BTrees.OOBTree.BTree(), spawnpoint=(Vector3(), Quaternion()))

		with open(luz_path, "rb") as file:
			luz = BitStream(file.read())
		### parse luz
		version = luz.read(c_uint)
		assert version in (38, 39, 40, 41), version
		luz.skip_read(4+4)
		if version >= 38:
			spawnpoint_position = luz.read(c_float), luz.read(c_float), luz.read(c_float)
			w, x, y, z = luz.read(c_float), luz.read(c_float), luz.read(c_float), luz.read(c_float)
			conn.root.world_data[world.value].spawnpoint = Vector3(*spawnpoint_position), Quaternion(x, y, z, w)

		if version >= 37:
			number_of_scenes = luz.read(c_uint)
		else:
			number_of_scenes = luz.read(c_ubyte)

		for _ in range(number_of_scenes):
			filename = luz.read(str, char_size=1, length_type=c_ubyte)
			luz.skip_read(8)
			luz.read(str, char_size=1, length_type=c_ubyte)
			luz.read(bytes, length=3)

			parse_lvl(conn, conn.root.world_data[world.value], os.path.join(os.path.dirname(luz_path), filename))

		assert luz.read(c_ubyte) == 0

		### terrain
		filename = luz.read(str, char_size=1, length_type=c_ubyte)
		name = luz.read(str, char_size=1, length_type=c_ubyte)
		description = luz.read(str, char_size=1, length_type=c_ubyte)

		### unknown
		for _ in range(luz.read(c_uint)):
			for _ in range(2):
				luz.skip_read(20)

		remaining_length = luz.read(c_uint)
		assert len(luz) - luz._read_offset//8 == remaining_length
		assert luz.read(c_uint) == 1

		### paths
		for _ in range(luz.read(c_uint)):
			path_version = luz.read(c_uint)
			path_name = luz.read(str, length_type=c_ubyte)
			path_type = luz.read(c_uint)
			luz.skip_read(8)

			if path_type == PathType.MovingPlatform:
				if path_version >= 18:
					unknown3 = luz.skip_read(1)
				elif path_version >= 13:
					unknown_str = luz.read(str, length_type=c_ubyte)

			elif path_type == PathType.Property:
				luz.skip_read(20)
				unknown_str1 = luz.read(str, length_type=c_ubyte)
				unknown_str2 = luz.read(str, length_type=c_uint)
				luz.skip_read(36)

			elif path_type == PathType.Camera:
				unknown_str = luz.read(str, length_type=c_ubyte)
				if path_version >= 14:
					unknown3 = luz.skip_read(1)

			elif path_type == PathType.Spawner:
				spawn_lot = luz.read(c_uint)
				unknown3 = luz.read(c_uint), luz.read(c_int), luz.read(c_uint)
				object_id = luz.read(c_int64)
				unknown4 = luz.read(c_ubyte)
				spawner = Template(176, conn)(object_id, SimpleNamespace(db=conn.root))
				del spawner._v_server
				spawner.spawntemplate = spawn_lot
				if spawn_lot != 0:
					conn.root.world_data[world.value].objects[object_id] = spawner

			waypoints = []

			for _ in range(luz.read(c_uint)):
				position = luz.read(c_float), luz.read(c_float), luz.read(c_float)

				if path_type == PathType.MovingPlatform:
					rotation = luz.read(c_float), luz.read(c_float), luz.read(c_float), luz.read(c_float)
					waypoint_unknown2 = luz.read(c_ubyte)
					waypoint_unknown3 = luz.read(c_float)
					waypoint_unknown4 = luz.read(c_float)

					if path_version >= 13:
						waypoint_audio_guid_1 = luz.read(str, length_type=c_ubyte)
						waypoint_audio_guid_2 = luz.read(str, length_type=c_ubyte)

				elif path_type == PathType.Camera:
					luz.skip_read(36)

				elif path_type == PathType.Spawner:
					w, x, y, z = luz.read(c_float), luz.read(c_float), luz.read(c_float), luz.read(c_float)
					rotation = x, y, z, w

				elif path_type == PathType.Race:
					luz.skip_read(30)

				elif path_type == PathType.Rail:
					luz.skip_read(16)
					if path_version >= 17:
						luz.skip_read(4)

				if path_type in (PathType.Movement, PathType.Spawner, PathType.Rail):
					config = {}
					for _ in range(luz.read(c_uint)):
						config_name = luz.read(str, length_type=c_ubyte)
						config_type_and_value = luz.read(str, length_type=c_ubyte)
						try:
							config[config_name] = ldf.from_ldf_type_value(config_type_and_value)
						except ValueError:
							pass

				if path_type == PathType.MovingPlatform:
					waypoints.append((position, waypoint_unknown3, waypoint_unknown4))
				elif path_type == PathType.Spawner:
					spawn_vars = {}
					spawned_vars = {}
					script_vars = {}
					waypoints.append((position, rotation, spawn_vars, spawned_vars, script_vars))

			if path_type == PathType.MovingPlatform:
				conn.root.world_data[world.value].paths[path_name] = tuple(waypoints)
			elif path_type == PathType.Spawner:
				spawner.waypoints = tuple(waypoints)
