from pyraknet.bitstream import c_float, c_int64, c_ubyte, c_uint, c_ushort, ReadStream
from luserver.ldf import LDF
from luserver.world import BITS_LOCAL
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3
import scripts

def parse_config(config, triggers=None):
	spawned_vars = {}

	if "compTime" in config:
		spawned_vars["rebuild_complete_time"] = config["compTime"]
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
		spawned_vars["respawn_data"] = Vector3(*[float(i) for i in config["rspPos"].split("\x1f")]), Quaternion(*[float(i) for i in config["rspRot"].split("\x1f")])
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

class LVLImporter:
	def __init__(self, lvl_path, root, world_data, triggers):
		self.root = root
		self.world_data = world_data
		self.triggers = triggers
		with open(lvl_path, "rb") as file:
			self.lvl = ReadStream(file.read(), unlocked=True)

		self.parse_lvl()

	def parse_lvl(self):
		new_format = self.lvl.read(bytes, length=4) == b"CHNK"
		self.lvl.read_offset = 0
		if new_format:
			while True:
				if self.lvl.all_read():
					break
				assert self.lvl.read_offset // 8 % 16 == 0  # seems everything is aligned like this?
				start_pos = self.lvl.read_offset // 8
				assert self.lvl.read(bytes, length=4) == b"CHNK"
				chunktype = self.lvl.read(c_uint)
				assert self.lvl.read(c_ushort) == 1
				assert self.lvl.read(c_ushort) in (1, 2)
				chunk_length = self.lvl.read(c_uint)  # position of next CHNK relative to this CHNK
				data_pos = self.lvl.read(c_uint)
				self.lvl.read_offset = data_pos * 8
				assert self.lvl.read_offset // 8 % 16 == 0
				if chunktype == 2001:
					self.parse_chunk_type_2001()
				self.lvl.read_offset = (start_pos + chunk_length) * 8  # go to the next CHNK
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
			position = self.lvl.read(Vector3)
			w, x, y, z = self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float), self.lvl.read(c_float)
			rotation = Quaternion(x, y, z, w)
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
				spawned_vars.update(parse_config(config, self.triggers))

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

				self.world_data.objects[object_id] = lot, object_id, spawned_vars
