import asyncio
import logging

from ..amf3 import AMF3
from ..ldf import LDF, LDFDataType
from ..world import server, World
from ..math.vector import Vector3
from .command import ChatCommand, normal_bool, toggle_bool

log = logging.getLogger(__name__)

def toggle(obj, attr_name, toggle):
	if toggle is None:
		setattr(obj, attr_name, not getattr(obj, attr_name))
	else:
		setattr(obj, attr_name, toggle)

class Build(ChatCommand):
	def __init__(self):
		super().__init__("build")
		self.command.add_argument("type", type=int)

	def run(self, args, sender):
		sender.char.activate_brick_mode(build_type=args.type)

class Currency(ChatCommand):
	def __init__(self):
		super().__init__("currency")
		self.command.add_argument("amount", type=int)

	def run(self, args, sender):
		sender.char.set_currency(currency=sender.char.currency + args.amount, position=Vector3.zero)

class Dab(ChatCommand):
	def __init__(self):
		super().__init__("dab")

	def run(self, args, sender):
		sender.render.play_animation("cute-spin-exit")

class Dismount(ChatCommand):
	def __init__(self):
		super().__init__("dismount")

	def run(self, args, sender):
		sender.char.dismount()

class Everlasting(ChatCommand):
	def __init__(self):
		super().__init__("everlasting")
		self.command.add_argument("--enable", type=toggle_bool)

	def run(self, args, sender):
		toggle(sender.skill, "everlasting", args.enable)

class Faction(ChatCommand):
	def __init__(self):
		super().__init__("faction")
		self.command.add_argument("faction", type=int)

	def run(self, args, sender):
		sender.stats.faction = args.faction

class FlashingText(ChatCommand):
	def __init__(self):
		super().__init__("flashingtext", aliases=("ftext",))
		self.command.add_argument("text", nargs="+")

	def run(self, args, sender):
		sender.char.u_i_message_server_to_single_client(message_name=b"ToggleFlashingText", args=AMF3({"text": " ".join(args.text)}))

class Freeze(ChatCommand):
	def __init__(self):
		super().__init__("freeze")
		self.enabled = False
		self.lut_volume = None
		self.velocity = {}

	def run(self, args, sender):
		self.enabled = not self.enabled
		sender.render.play_n_d_audio_emitter(event_guid=b"{57cf736d-ab58-4f30-b4d6-afebf81caedd}", meta_event_name=b"")
		asyncio.get_event_loop().call_later(3.1, self.do_freeze, sender)

	def do_freeze(self, sender):
		if self.enabled:
			config = LDF()
			config.ldf_set("custom_script_client", LDFDataType.STRING, r"scripts\02_client\map\general\l_lut_volume.lua")
			config.ldf_set("LUT", LDFDataType.STRING, "lut_hue_volume.dds")
			config.ldf_set("renderDisabled", LDFDataType.BOOLEAN, True)
			spawn_config = {"config": config, "scale": 1000, "position": sender.physics.position}
			self.lut_volume = server.spawn_object(5652, spawn_config)

		for obj in server.game_objects.values():
			if hasattr(obj, "render") and (not self.enabled or obj != sender):
					obj.render.freeze_animation(do_freeze=self.enabled)
			if hasattr(obj, "char"):
				#obj.render.play_f_x_effect(name=b"", effect_type="on-anim", effect_id=4747)
				if self.enabled and obj != sender:
					self.velocity[obj] = Vector3(obj.physics.velocity)
					obj.char.set_gravity_scale(0)
					obj.char.teleport(ignore_y=False, pos=obj.physics.position-Vector3.up*2, x=0, y=0, z=0)
					obj.char.force_camera_target_cycle(optional_target=sender)
				else:
					obj.char.set_gravity_scale(1)
					if obj in self.velocity and self.velocity[obj].sq_magnitude() > 0.01:
						obj.char.knockback(vector=self.velocity[obj])
					obj.char.force_camera_target_cycle(optional_target=obj)

				if not self.enabled or obj != sender:
					obj.char.set_user_ctrl_comp_pause(paused=self.enabled)

		if not self.enabled:
			self.velocity.clear()
			server.replica_manager.destruct(self.lut_volume)

class Glow(ChatCommand):
	def __init__(self):
		super().__init__("glow")

	def run(self, args, sender):
		if sender.char.rebuilding == 0:
			sender.char.rebuilding = 1
		else:
			sender.char.rebuilding = 0

class Gravity(ChatCommand):
	def __init__(self):
		super().__init__("gravity")
		self.command.add_argument("--scale", type=float, default=1)

	def run(self, args, sender):
		sender.char.set_gravity_scale(args.scale)

class Help(ChatCommand):
	def __init__(self):
		super().__init__("help")

	def run(self, args, sender):
		server.chat.sys_msg_sender("Please use -h / --help for help.")

class HighStats(ChatCommand):
	def __init__(self):
		super().__init__("highstats")

	def run(self, args, sender):
		sender.stats.max_life = 99
		sender.stats.max_armor = 99
		sender.stats.max_imagination = 99
		sender.stats.refill_stats()

class Invisibility(ChatCommand):
	# not working
	def __init__(self):
		super().__init__("invisibility", aliases=("invis",))

	def run(self, args, sender):
		sender.char.toggle_g_m_invis()

class Jetpack(ChatCommand):
	def __init__(self):
		super().__init__("jetpack")
		self.command.add_argument("enable", type=normal_bool)
		self.command.add_argument("--hover", action="store_true")
		self.command.add_argument("--bypass-checks", type=normal_bool, default=True)
		self.command.add_argument("--effect-id", type=int, default=167)
		self.command.add_argument("--air-speed", type=float, default=20)
		self.command.add_argument("--max-air-speed", type=float, default=30)
		self.command.add_argument("--vertical-velocity", type=float, default=1.5)

	def run(self, args, sender):
		sender.char.set_jet_pack_mode(args.enable, args.hover, args.bypass_checks, args.effect_id, args.air_speed, args.max_air_speed, args.vertical_velocity)

class Knockback(ChatCommand):
	def __init__(self):
		super().__init__("knockback")
		self.command.add_argument("direction", nargs=3, type=float)

	def run(self, args, sender):
		args.direction = Vector3(*args.direction)
		sender.char.knockback(vector=args.direction)

class Level(ChatCommand):
	def __init__(self):
		super().__init__("level", description="Set player level.")
		self.command.add_argument("--level", type=int, default=45)

	def run(self, args, sender):
		sender.char.level = args.level
		server.chat.sys_msg_sender("Level will appear set on next login.")

class Location(ChatCommand):
	def __init__(self):
		super().__init__("location", aliases=("locate", "loc"), description="Print your location.")
		self.command.add_argument("--player")

	def run(self, args, sender):
		if args.player:
			for obj in server.game_objects.values():
				if hasattr(obj, "char") and obj.name.startswith(args.player):
					server.chat.sys_msg_sender(args.player, "is at%f %f %f" % (obj.physics.position.x, obj.physics.position.y, obj.physics.position.z))
					if obj.char.world[0] != server.world_id[0]:
						server.chat.sys_msg_sender(World(obj.char.world[0]))
					break

class RefillStats(ChatCommand):
	def __init__(self):
		super().__init__("refillstats")

	def run(self, args, sender):
		sender.stats.refill_stats()

class Rules(ChatCommand):
	def __init__(self):
		super().__init__("rules")

	def run(self, args, sender):
		context = {"bScroll": True}
		for i, page in enumerate(server.db.config["rules"]):
			context["PAGE%i" % i] = page
		sender.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "Story", "context": context}))

class SetFlag(ChatCommand):
	def __init__(self):
		super().__init__("setflag")
		self.command.add_argument("flag_id", type=int)
		self.command.add_argument("--value", type=normal_bool, default=True)

	def run(self, args, sender):
		sender.char.set_flag(args.value, args.flag_id)

class SetRespawn(ChatCommand):
	def __init__(self):
		super().__init__("setrespawn")

	def run(self, args, sender):
		sender.char.player_reached_respawn_checkpoint(sender.physics.position, sender.physics.rotation)

class ShowGMStatus(ChatCommand):
	def __init__(self):
		super().__init__("showgmstatus", description="Change whether you appear as 'Mythran' to other players.")
		self.command.add_argument("--enable", type=toggle_bool)

	def run(self, args, sender):
		if sender.char.account.gm_level == 0:
			sender.char.account.show_gm_status = False
			return
		toggle(sender.char, "show_gm_status", args.enable)

class Speak(ChatCommand):
	def __init__(self):
		super().__init__("speak")
		self.command.add_argument("object")

	def run(self, args, sender):
		for obj in server.game_objects.values():
			if obj.name == args.object:
				obj.add_handler("on_private_chat_message", Speak.speak)
				server.chat.send_private_chat_message("!"+args.object, "Everything you type will be spoken by the selected object.", sender)
				return
		server.chat.sys_msg_sender("Object not found")

	@staticmethod
	def speak(self, sender, text):
		server.chat.send_general_chat_message(self, text)

class Spectate(ChatCommand):
	def __init__(self):
		super().__init__("spectate")
		self.command.add_argument("name")

	def run(self, args, sender):
		args.name = args.name.lower()
		for obj in server.game_objects.values():
			if obj.name.lower().startswith(args.name):
				sender.char.force_camera_target_cycle(optional_target=obj)

class Tags(ChatCommand):
	def __init__(self):
		super().__init__("tags")
		self.command.add_argument("player")
		self.command.add_argument("--action", choices=("add", "clear", "remove", "show"), default="show")
		self.command.add_argument("--tag", nargs="+")

	def run(self, args, sender):
		player = server.find_player_by_name(args.player)
		if player is None:
			return
		if args.action == "add":
			if args.tag is None:
				server.chat.sys_msg_sender("specify --tag")
				return
			args.tag = " ".join(args.tag)
			if len(", ".join(player.char.tags)+", "+args.tag) > 255:
				server.chat.sys_msg_sender("tags too long")
				return
			player.char.tags.append(args.tag)
			player.char.attr_changed("tags")

		elif args.action == "clear":
			player.char.tags.clear()
			player.char.attr_changed("tags")

		elif args.action == "remove":
			if args.tag is None:
				server.chat.sys_msg_sender("specify --tag")
				return
			args.tag = " ".join(args.tag)
			player.char.tags.remove(args.tag)
			player.char.attr_changed("tags")

		elif args.action == "show":
			server.chat.sys_msg_sender(player.char.tags)

class Teleport(ChatCommand):
	def __init__(self):
		super().__init__("teleport", aliases=("tp",))
		self.command.add_argument("--position", nargs=3, type=float)
		self.command.add_argument("--player")
		self.command.add_argument("--y", action="store_false")

	def run(self, args, sender):
		if args.position:
			pos = Vector3(*args.position)

		elif args.player:
			args.player = args.player.lower()
			for obj in server.game_objects.values():
				if hasattr(obj, "char") and obj.name.lower().startswith(args.player):
					pos = obj.physics.position
					break
			else:
				server.chat.sys_msg_sender("no player found")
				return
		else:
			pos = Vector3(sender.physics.position.x, 100000, sender.physics.position.z)

		sender.char.teleport(ignore_y=args.y, pos=pos, x=0, y=0, z=0)

class Text(ChatCommand):
	def __init__(self):
		super().__init__("text")
		self.command.add_argument("text", nargs="+")

	def run(self, args, sender):
		sender.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "Story", "context": {"text": " ".join(args.text)}}))

class UnlockEmote(ChatCommand):
	def __init__(self):
		super().__init__("unlockemote")
		self.command.add_argument("id", type=int)

	def run(self, args, sender):
		sender.char.set_emote_lock_state(lock=False, emote_id=args.id)

class Vendor(ChatCommand):
	ALL_ITEMS = 20, 21, 80, 89, 118, 125, 130, 131, 1883, 1889, 1891, 1966, 2198, 2620, 2632, 2633, 2635, 2641, 2642, 2670, 2844, 2846, 2867, 2946, 2985, 2986, 2989, 2990, 2993, 2994, 2995, 2996, 2997, 2998, 2999, 3011, 3012, 3038, 3039, 3040, 3053, 3063, 3100, 3206, 3825, 3906, 4015, 4757, 4770, 4792, 4799, 4924, 4927, 4939, 4989, 4991, 4992, 4995, 4996, 5628, 5645, 5646, 5654, 5658, 5674, 5676, 5687, 5693, 5695, 5707, 5711, 5832, 5833, 5834, 5835, 5836, 5837, 5841, 5873, 5949, 5950, 5955, 5964, 6086, 6195, 6201, 6207, 6233, 6246, 6248, 6265, 6288, 6328, 6332, 6333, 6334, 6339, 6393, 6494, 6496, 6497, 6498, 6499, 6500, 6501, 6502, 6503, 6512, 6544, 6600, 6612, 6622, 6642, 6643, 6644, 6645, 6646, 6647, 6713, 6790, 6791, 6795, 6844, 6847, 6848, 6853, 6860, 6861, 6862, 6863, 6864, 6865, 6866, 6871, 6872, 6882, 6883, 6884, 6885, 6886, 6905, 6906, 6907, 6908, 6912, 6921, 6925, 6926, 6927, 6928, 6929, 6930, 6931, 6932, 6933, 6934, 6935, 6937, 6967, 6969, 6970, 6971, 7013, 7035, 7039, 7044, 7084, 7089, 7101, 7102, 7103, 7104, 7105, 7111, 7112, 7113, 7114, 7115, 7116, 7133, 7148, 7150, 7225, 7292, 7311, 7313, 7333, 7339, 7355, 7356, 7357, 7358, 7359, 7360, 7361, 7362, 7363, 7364, 7365, 7366, 7367, 7368, 7369, 7370, 7371, 7372, 7373, 7374, 7375, 7376, 7377, 7378, 7379, 7380, 7381, 7382, 7383, 7384, 7385, 7386, 7387, 7388, 7389, 7390, 7391, 7392, 7393, 7394, 7395, 7396, 7397, 7398, 7399, 7400, 7401, 7402, 7403, 7404, 7405, 7406, 7407, 7408, 7409, 7415, 7416, 7417, 7442, 7443, 7444, 7445, 7446, 7447, 7448, 7449, 7450, 7451, 7452, 7453, 7454, 7455, 7456, 7457, 7458, 7459, 7460, 7461, 7462, 7463, 7464, 7465, 7466, 7467, 7468, 7469, 7470, 7471, 7472, 7473, 7474, 7475, 7476, 7477, 7478, 7479, 7480, 7481, 7482, 7483, 7484, 7485, 7486, 7487, 7488, 7489, 7490, 7491, 7492, 7493, 7494, 7495, 7496, 7497, 7498, 7499, 7500, 7501, 7502, 7503, 7504, 7505, 7506, 7507, 7508, 7509, 7510, 7511, 7512, 7513, 7514, 7515, 7516, 7517, 7518, 7519, 7520, 7521, 7522, 7523, 7524, 7525, 7526, 7527, 7528, 7529, 7530, 7531, 7532, 7533, 7534, 7535, 7536, 7537, 7538, 7539, 7540, 7541, 7542, 7543, 7544, 7545, 7546, 7547, 7548, 7550, 7555, 7556, 7557, 7558, 7586, 7589, 7590, 7591, 7592, 7601, 7627, 7628, 7629, 7630, 7631, 7632, 7633, 7634, 7635, 7636, 7641, 7661, 7690, 7724, 7725, 7778, 7779, 7787, 7788, 7794, 7936, 7985, 7989, 7994, 7998, 7999, 8007, 8009, 8012, 8016, 8017, 8021, 8027, 8028, 8029, 8030, 8031, 8032, 8033, 8034, 8080, 8081, 8086, 8087, 8110, 8111, 8144, 8145, 8156, 8157, 8158, 8162, 8169, 8170, 8273, 8274, 8275, 8276, 8285, 8286, 8287, 8288, 8291, 8318, 8319, 8320, 8321, 8343, 8348, 8351, 8353, 8354, 8356, 8357, 8360, 8361, 8363, 8365, 8366, 8367, 8371, 8375, 8376, 8456, 8457, 8458, 8459, 8460, 8461, 8462, 8463, 8464, 8465, 8466, 8467, 8508, 8515, 8518, 8519, 8523, 8545, 8566, 8584, 8585, 8586, 8587, 8588, 8589, 8590, 8591, 8592, 8593, 8594, 8595, 8596, 8597, 8598, 8601, 8602, 8603, 8604, 8605, 8606, 8607, 8608, 8609, 8611, 8612, 8613, 8614, 8615, 8616, 8617, 8618, 8620, 8621, 8622, 8623, 8624, 8625, 8626, 8627, 8628, 8629, 8630, 8631, 8637, 8638, 8639, 8640, 8641, 8642, 8643, 8644, 8645, 8646, 8647, 8648, 8649, 8650, 8651, 8655, 8664, 8666, 8667, 8673, 8674, 8676, 8680, 8681, 8682, 8683, 8684, 8685, 9259, 9466, 9467, 9468, 9469, 9470, 9471, 9472, 9525, 9528, 9531, 9532, 9533, 9595, 9603, 9614, 9619, 9620, 9623, 9624, 9625, 9626, 9681, 9682, 9683, 9684, 9685, 9686, 9687, 9688, 9689, 9690, 9700, 9721, 9722, 9723, 9724, 9725, 9726, 9731, 9773, 9774, 9775, 9776, 9787, 9788, 9815, 9816, 9817, 9818, 9819, 9820, 9829, 9875, 9935, 9936, 9943, 9944, 9945, 9946, 9947, 9948, 9949, 9950, 9951, 9953, 9954, 9955, 9963, 9964, 9965, 9966, 9967, 9968, 9969, 9970, 9971, 9972, 9973, 9974, 9975, 9976, 9994, 9995, 9996, 9997, 9998, 9999, 10000, 10005, 10012, 10021, 10038, 10045, 10052, 10053, 10054, 10066, 10095, 10096, 10121, 10122, 10123, 10124, 10125, 10127, 10128, 10129, 10130, 10131, 10154, 10155, 10156, 10157, 10158, 10165, 10167, 10298, 10312, 10316, 10396, 10397, 10398, 10399, 10400, 10401, 10417, 10431, 10432, 10433, 10434, 10436, 10458, 10480, 10481, 10482, 10483, 10484, 10485, 10486, 10487, 10488, 10513, 10514, 10515, 10516, 10519, 10520, 10521, 10698, 10699, 10700, 10701, 10702, 11160, 11161, 11162, 11181, 11195, 11207, 11228, 11256, 11272, 11283, 11286, 11287, 11291, 11292, 11293, 11299, 11303, 11304, 11309, 11310, 11311, 11312, 11313, 11314, 11315, 11316, 11317, 11318, 11385, 11429, 11432, 11458, 11459, 11460, 11461, 11462, 11463, 11909, 11922, 11923, 11924, 11925, 11926, 11927, 11928, 11929, 11931, 11932, 11933, 11934, 12043, 12091, 12092, 12093, 12094, 12095, 12098, 12101, 12102, 12103, 12107, 12108, 12109, 12110, 12114, 12115, 12116, 12128, 12129, 12130, 12131, 12219, 12220, 12221, 12222, 12223, 12224, 12225, 12226, 12231, 12240, 12241, 12242, 12252, 12281, 12282, 12284, 12288, 12295, 12296, 12297, 12298, 12299, 12300, 12303, 12304, 12305, 12308, 12309, 12310, 12311, 12312, 12313, 12314, 12315, 12316, 12319, 12338, 12339, 12380, 12389, 12424, 12425, 12426, 12427, 12428, 12435, 12437, 12447, 12448, 12449, 12450, 12451, 12462, 12470, 12471, 12472, 12474, 12486, 12490, 12512, 12513, 12518, 12520, 12521, 12522, 12523, 12525, 12526, 12527, 12528, 12529, 12530, 12541, 12546, 12549, 12554, 12557, 12558, 12559, 12560, 12561, 12562, 12563, 12564, 12565, 12567, 12569, 12574, 12592, 12593, 12594, 12595, 12596, 12597, 12598, 12599, 12601, 12603, 12606, 12607, 12608, 12613, 12622, 12623, 12624, 12625, 12627, 12630, 12636, 12637, 12638, 12642, 12647, 12648, 12649, 12650, 12651, 12656, 12657, 12658, 12659, 12667, 12669, 12682, 12688, 12689, 12690, 12691, 12693, 12695, 12696, 12698, 12700, 12702, 12705, 12706, 12707, 12708, 12709, 12710, 12711, 12712, 12714, 12715, 12718, 12719, 12720, 12721, 12722, 12723, 12724, 12725, 12726, 12728, 12729, 12730, 12731, 12732, 12733, 12734, 12735, 12737, 12740, 12741, 12747, 12748, 12749, 12753, 12754, 12755, 12756, 12758, 12759, 12760, 12761, 12762, 12763, 12764, 12765, 12766, 12767, 12768, 12769, 12770, 12771, 12774, 12775, 12776, 12777, 12778, 12779, 12780, 12782, 12783, 12784, 12785, 12786, 12788, 12789, 12792, 12793, 12796, 12797, 12798, 12801, 12802, 12809, 12816, 12817, 12886, 12889, 12890, 12891, 12912, 12913, 12914, 12915, 12921, 12922, 12923, 12924, 12927, 12945, 12946, 12947, 12949, 12950, 12951, 12952, 12953, 12954, 12955, 12956, 12957, 12958, 12959, 12960, 12961, 12962, 12963, 12964, 12965, 12966, 12967, 12968, 12969, 12976, 12977, 12978, 12981, 12982, 12983, 12984, 12985, 12986, 12987, 12988, 12989, 12990, 12991, 12992, 12993, 12994, 12995, 13014, 13073, 13097, 13099, 13102, 13103, 13109, 13110, 13112, 13113, 13117, 13134, 13135, 13136, 13137, 13138, 13139, 13140, 13141, 13143, 13144, 13145, 13146, 13279, 13281, 13282, 13283, 13284, 13285, 13286, 13287, 13288, 13289, 13290, 13291, 13301, 13302, 13310, 13311, 13423, 13424, 13426, 13525, 13526, 13527, 13529, 13544, 13545, 13546, 13547, 13548, 13549, 13550, 13551, 13574, 13575, 13576, 13577, 13579, 13580, 13581, 13582, 13583, 13584, 13585, 13586, 13603, 13604, 13605, 13606, 13617, 13623, 13624, 13625, 13737, 13741, 13746, 13747, 13748, 13749, 13750, 13751, 13752, 13753, 13754, 13755, 13756, 13757, 13758, 13759, 13760, 13761, 13762, 13763, 13777, 13779, 13781, 13784, 13786, 13803, 13804, 13805, 13814, 13836, 13837, 13838, 13839, 13840, 13841, 13890, 13891, 13892, 13910, 13911, 13912, 13913, 13914, 13915, 13916, 13917, 13918, 13919, 13920, 13921, 13922, 13923, 13934, 13942, 13949, 13950, 13965, 13966, 13967, 13968, 13969, 13975, 13976, 13977, 13978, 13979, 13980, 13981, 13982, 13983, 13986, 13987, 13988, 13989, 13991, 13992, 13993, 14014, 14015, 14016, 14017, 14018, 14019, 14020, 14021, 14022, 14083, 14091, 14092, 14093, 14095, 14096, 14097, 14098, 14099, 14100, 14101, 14102, 14103, 14104, 14105, 14106, 14107, 14108, 14109, 14112, 14113, 14114, 14115, 14116, 14117, 14118, 14119, 14120, 14121, 14122, 14123, 14124, 14125, 14126, 14127, 14128, 14132, 14136, 14147, 14148, 14158, 14159, 14160, 14161, 14162, 14163, 14164, 14165, 14166, 14167, 14168, 14172, 14173, 14174, 14181, 14185, 14186, 14190, 14191, 14192, 14193, 14194, 14195, 14196, 14197, 14198, 14240, 14305, 14315, 14316, 14317, 14318, 14319, 14320, 14321, 14322, 14323, 14324, 14325, 14326, 14353, 14354, 14355, 14356, 14357, 14358, 14359, 14360, 14361, 14362, 14363, 14364, 14378, 14431, 14432, 14433, 14434, 14467, 14468, 14469, 14470, 14471, 14472, 14474, 14475, 14484, 14486, 14487, 14488, 14489, 14490, 14497, 14499, 14500, 14502, 14503, 14504, 14506, 14507, 14508, 14509, 14511, 14512, 14559, 14560, 14561, 14562, 14563, 14564, 14565, 14566, 14567, 14568, 14569, 14570, 14571, 14591, 14592, 14604, 14606, 14669, 14675, 14678, 14679, 14680, 14682, 14683, 14684, 14685, 14691, 14705, 14713, 14714, 14715, 14723, 14724, 14725, 14726, 14730, 14731, 14734, 14736, 14737, 14764, 14767, 14768, 14769, 14770, 14771, 14772, 14773, 14774, 14775, 14776, 14777, 14778, 14780, 14798, 14801, 14804, 14830, 14833, 14834, 14837, 14841, 15843, 15844, 15845, 15892, 15909, 15911, 15914, 15916, 15917, 15943, 15944, 15946, 15948, 15956, 15957, 15975, 15976, 15977, 15978, 15979, 15980, 15982, 15983, 16012, 16023, 16035, 16037, 16038, 16041, 16052, 16053, 16054, 16055, 16059, 16060, 16063, 16064, 16065, 16066, 16067, 16068, 16069, 16070, 16082, 16083, 16084, 16085, 16086, 16087, 16134, 16146, 16147, 16148, 16149, 16150, 16151, 16179, 16180, 16181, 16182, 16183, 16184, 16185, 16186, 16187, 16188, 16189, 16190, 16251, 16266, 16267, 16268, 16269, 16270, 16271, 16272, 16273, 16274, 16275, 16276, 16277, 16480, 16514, 16551, 16587, 16588, 16594, 16595, 16596, 16597, 16598, 16599, 16600, 16601, 16602, 16605, 16606, 16607, 16608, 16609, 16610, 16611, 16612, 16613, 16614, 16615, 16616, 16620, 16621, 16622, 16629, 16632, 16633, 16634, 16635, 16636, 16637, 16638, 16639, 16640, 16644, 16647, 16682, 2097196

	ALL_MODELS = 6027, 6028, 6029, 6030, 6031, 6032, 6033, 6034, 6035, 6036, 6037, 6039, 6040, 6041, 6043, 6044, 6045, 6053, 6054, 6055, 6056, 6058, 6060, 6064, 6065, 6066, 6068, 6071, 6072, 6518, 6519, 6520, 6521, 6522, 6523, 6524, 6525, 6526, 6774, 6776, 6778, 6779, 6781, 6782, 6836, 6839, 6840, 6841, 6869, 6870, 6906, 6908, 6941, 6942, 7057, 7059, 7060, 7061, 7122, 7123, 7124, 7125, 7126, 7127, 7134, 7135, 7758, 7759, 7761, 7766, 7767, 7768, 7769, 7770, 7771, 7773, 7774, 7775, 7808, 7812, 7813, 7818, 7822, 7825, 7826, 7827, 7828, 7829, 7830, 7832, 7970, 7971, 7974, 8049, 8050, 8051, 8055, 8066, 8067, 8068, 8069, 8073, 8077, 8170, 8270, 8401, 9484, 9485, 9486, 9488, 9489, 9490, 9491, 9492, 9493, 9495, 9496, 9497, 9535, 9537, 9538, 9540, 9545, 9546, 9547, 9548, 9549, 9550, 9551, 9552, 9553, 9554, 9555, 9557, 9559, 9561, 9564, 9565, 9567, 9568, 9570, 9574, 9575, 9576, 9577, 9578, 9579, 9580, 9581, 9582, 9583, 9584, 9585, 9586, 9587, 9590, 9591, 9596, 9597, 9598, 9599, 9600, 9601, 9602, 9604, 9605, 9606, 9607, 9608, 9629, 9646, 9647, 9648, 9649, 9650, 9651, 9652, 9653, 9654, 9655, 9656, 9657, 9658, 9659, 9660, 9661, 9662, 9663, 9664, 9665, 9666, 9667, 9668, 9669, 9670, 9671, 9672, 9673, 9674, 9675, 9676, 9677, 9678, 9721, 9722, 9723, 9724, 9725, 9726, 9773, 9775, 9776, 9811, 9812, 9813, 9814, 9908, 9909, 9910, 9911, 9912, 9913, 9914, 9915, 9916, 9917, 9918, 9919, 9920, 9921, 9922, 9923, 9924, 10069, 10070, 10071, 10072, 10073, 10074, 10075, 10076, 10077, 10078, 10079, 10080, 10081, 10082, 10083, 10084, 10085, 10086, 10087, 10088, 10089, 10090, 10091, 10092, 10093, 10094, 10280, 10289, 10316, 10318, 10319, 10320, 10321, 10322, 10323, 10324, 10325, 10326, 10327, 10328, 10329, 10330, 10331, 10332, 10333, 10334, 10335, 10336, 10337, 10338, 10339, 10340, 10341, 10342, 10343, 10344, 10345, 10346, 10347, 10348, 10349, 10350, 10351, 10352, 10353, 10354, 10355, 10356, 10357, 10358, 10359, 10360, 10361, 10362, 10363, 10364, 10365, 10366, 10367, 10368, 10369, 10370, 10371, 10372, 10373, 10374, 10375, 10385, 10396, 10397, 10398, 10399, 10400, 10401, 10417, 10513, 10514, 10515, 10516, 10700, 10705, 10706, 10707, 10708, 10709, 10710, 10750, 10751, 10752, 10753, 10754, 10755, 10756, 10757, 10758, 10759, 10760, 10761, 10762, 10763, 10764, 10765, 10766, 10767, 10768, 10769, 10770, 10771, 10772, 10773, 10774, 10775, 10776, 10777, 10778, 10779, 10780, 10781, 10782, 10783, 10788, 10789, 10790, 10791, 10792, 10793, 10794, 10795, 10796, 10797, 10798, 10799, 10800, 10801, 10802, 10803, 10804, 10805, 10806, 10807, 10808, 10809, 10810, 10811, 10812, 10813, 10814, 10815, 10816, 10817, 10818, 10819, 10820, 10821, 10822, 10823, 10824, 10825, 10826, 10827, 10828, 10829, 10830, 10831, 10832, 10833, 10834, 10835, 10836, 10837, 10838, 10839, 10840, 10841, 10842, 10843, 10844, 10845, 10846, 10847, 10848, 10849, 10850, 10851, 10852, 10853, 10854, 10855, 10856, 10857, 10858, 10859, 10860, 10861, 10862, 10864, 10865, 10866, 10867, 10868, 10869, 10870, 10871, 10872, 10873, 10874, 10875, 10876, 10877, 10878, 10879, 10880, 10882, 10883, 10884, 10887, 10888, 10889, 10890, 10999, 11001, 11005, 11007, 11009, 11011, 11111, 11116, 11160, 11161, 11162, 11197, 11198, 11199, 11200, 11201, 11526, 11527, 11528, 11529, 11530, 11531, 11532, 11533, 11534, 11535, 11536, 11537, 11538, 11539, 11540, 11541, 11542, 11543, 11544, 11545, 11546, 11547, 11548, 11549, 11550, 11551, 11552, 11553, 11554, 11555, 11556, 11557, 11558, 11559, 11560, 11561, 11562, 11563, 11564, 11565, 11566, 11567, 11568, 11569, 11570, 11571, 11572, 11573, 11574, 11575, 11576, 11577, 11578, 11579, 11580, 11581, 11582, 11583, 11584, 11585, 11586, 11587, 11588, 11589, 11590, 11591, 11592, 11593, 11594, 11595, 11596, 11597, 11598, 11599, 11600, 11601, 11602, 11603, 11604, 11605, 11606, 11607, 11608, 11609, 11610, 11611, 11612, 11613, 11614, 11615, 11616, 11617, 11618, 11619, 11620, 11621, 11622, 11623, 11624, 11625, 11626, 11627, 11628, 11629, 11630, 11631, 11632, 11633, 11634, 11635, 11636, 11637, 11638, 11639, 11640, 11641, 11642, 11643, 11644, 11645, 11646, 11647, 11648, 11649, 11650, 11651, 11652, 11653, 11654, 11655, 11656, 11657, 11658, 11659, 11660, 11661, 11662, 11663, 11664, 11665, 11666, 11667, 11668, 11669, 11670, 11671, 11672, 11673, 11674, 11675, 11676, 11677, 11678, 11679, 11680, 11681, 11682, 11683, 11684, 11685, 11686, 11687, 11688, 11689, 11690, 11691, 11692, 11693, 11694, 11695, 11696, 11697, 11698, 11699, 11700, 11701, 11702, 11703, 11704, 11705, 11706, 11707, 11708, 11709, 11710, 11711, 11712, 11713, 11714, 11715, 11716, 11717, 11718, 11719, 11720, 11721, 11722, 11723, 11724, 11725, 11726, 11727, 11728, 11729, 11730, 11731, 11732, 11733, 11734, 11735, 11736, 11737, 11738, 11739, 11740, 11741, 11742, 11743, 11744, 11745, 11746, 11747, 11748, 11749, 11750, 11751, 11752, 11753, 11754, 11755, 11756, 11757, 11758, 11759, 11760, 11761, 11762, 11763, 11764, 11765, 11766, 11767, 11768, 11769, 11770, 11771, 11772, 11773, 11774, 11775, 11776, 11777, 11778, 11779, 11780, 11781, 11782, 11783, 11784, 11785, 11786, 11787, 11788, 11789, 11790, 11791, 11792, 11793, 11794, 11795, 11796, 11797, 11798, 11799, 11800, 11801, 11802, 11803, 11804, 11805, 11806, 11807, 11808, 11809, 11810, 11811, 11812, 11813, 11814, 11815, 11816, 11817, 11818, 11819, 11820, 11821, 11822, 11823, 11824, 11825, 11826, 11827, 11828, 11829, 11830, 11831, 11832, 11833, 11834, 11835, 11836, 11837, 11838, 11839, 11840, 11841, 11842, 11843, 11844, 11845, 11846, 11847, 11848, 11849, 11850, 11851, 11852, 11853, 11854, 11855, 11856, 11857, 11858, 11859, 11860, 11861, 11862, 11863, 11864, 11865, 11866, 11867, 11868, 11869, 11870, 11871, 11872, 11873, 11874, 11875, 11876, 11877, 11878, 11879, 11880, 11881, 11882, 11883, 11884, 11885, 11886, 11887, 11888, 11889, 11890, 11891, 11892, 11893, 12231, 12282, 12348, 12349, 12350, 12351, 12352, 12353, 12354, 12355, 12356, 12357, 12495, 12496, 12497, 12498, 12499, 12500, 12501, 12502, 12503, 12504, 12505, 12506, 12507, 12508, 12521, 12522, 12523, 12524, 12525, 12526, 12527, 12528, 12529, 12557, 12558, 12559, 12560, 12818, 13002, 13003, 13004, 13117, 13151, 13152, 13153, 13154, 13155, 13156, 13157, 13158, 13159, 13160, 13161, 13427, 13604, 13623, 13624, 13625, 13639, 13640, 13641, 13642, 13643, 13644, 13645, 13646, 13647, 13648, 13649, 13650, 13651, 13652, 13653, 13654, 13655, 13656, 13657, 13658, 13659, 13660, 13661, 13662, 13663, 13664, 13665, 13666, 13667, 13668, 13669, 13670, 13671, 13672, 13673, 13674, 13675, 13676, 13677, 13678, 13679, 13680, 13681, 13682, 13683, 13684, 13685, 13686, 13687, 13688, 13689, 13690, 13691, 13692, 13693, 13694, 13695, 13696, 13697, 13698, 13699, 13700, 13701, 13702, 13703, 13704, 13705, 13706, 13707, 13708, 13709, 13710, 13711, 13712, 13713, 13714, 13715, 13716, 13717, 13718, 13719, 13720, 13721, 13722, 13723, 13724, 13725, 13726, 13727, 13728, 14203, 14766, 15949, 15950, 15951, 15952, 16247, 16248, 16249, 16250, 16517, 16518, 16519, 16520, 16521, 16523, 16524, 16525, 16526, 16527, 16528, 16529, 16530, 16531, 16532, 16533, 16534, 16535, 16536, 16537, 16538, 16539, 16540, 16541, 16542, 16543, 16544, 16545, 16546, 16565, 16566, 16567, 16568, 16569, 16570, 16571, 16572, 16573, 16574, 16575, 16576, 16577, 16578, 16579, 16580, 16581, 16582, 16583, 16584, 16585
	MOD_ITEMS = 1727, 2243, 3293, 5873, 6407, 13424

	def __init__(self):
		super().__init__("vendor")
		self.command.add_argument("--items", choices=("clothing", "items", "mod", "models"), default="items")

	def run(self, args, sender):
		if args.items == "clothing":
			server.spawn_object(3917, {"parent": sender})
			return
		if args.items == "items":
			items = Vendor.ALL_ITEMS
		elif args.items == "mod":
			items = Vendor.MOD_ITEMS
		elif args.items == "models":
			items = Vendor.ALL_MODELS

		vendor = server.spawn_object(6875, {"name": "Vendor of Everything", "parent": sender})
		vendor.vendor.items_for_sale = [(lot, False, 0) for lot in items]

class WorldCommand(ChatCommand):
	def __init__(self):
		super().__init__("world", description="Go to world")
		self.command.add_argument("name")

	def run(self, args, sender):
		asyncio.ensure_future(sender.char.transfer_to_world((World[args.name].value, 0, 0), respawn_point_name=""))
