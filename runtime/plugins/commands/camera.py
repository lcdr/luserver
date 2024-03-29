from luserver.ldf import LDF, LDFDataType
from luserver.world import server
from luserver.interfaces.plugin import ChatCommand
from luserver.math.vector import Vector3

# other camera effects are "celebrate" and "attach", these haven't been completely investigated yet

class CamLookAt(ChatCommand):
	def __init__(self):
		super().__init__("camlookat")
		group = self.command.add_mutually_exclusive_group(required=True)
		group.add_argument("--object")
		group.add_argument("--pos", nargs=3, type=float)
		self.command.add_argument("--duration", type=float, default=5)
		self.command.add_argument("--fov", type=float, default=30)
		self.command.add_argument("--leadin", type=float, default=5)
		self.command.add_argument("--leadout", type=float, default=5)
		self.command.add_argument("--lag", type=float, default=5)
		self.command.add_argument("--voffset", type=float, default=4)

	def run(self, args, sender):
		config = LDF()
		if args.object:
			for obj in server.game_objects.values():
				if obj.name == args.object:
					config.ldf_set("objectID", LDFDataType.STRING, str(obj.object_id))
					break
			else:
				server.chat.sys_msg_sender("Object not found")
				return
		else:
			pos = Vector3(*args.pos)
			config.ldf_set("xPos", LDFDataType.FLOAT, pos.x)
			config.ldf_set("yPos", LDFDataType.FLOAT, pos.y)
			config.ldf_set("zPos", LDFDataType.FLOAT, pos.z)

		config.ldf_set("leadIn", LDFDataType.FLOAT, args.leadin)
		config.ldf_set("leadOut", LDFDataType.FLOAT, args.leadout)
		config.ldf_set("lag", LDFDataType.FLOAT, args.lag)
		config.ldf_set("FOV", LDFDataType.FLOAT, args.fov)
		config.ldf_set("verticalOffset", LDFDataType.FLOAT, args.voffset)
		sender.char.camera.add_camera_effect(config, effect_id="lookat", effect_type="lookAt", duration=args.duration)

class CamShake(ChatCommand):
	def __init__(self):
		super().__init__("camshake")
		self.command.add_argument("--duration", type=float, default=1)
		self.command.add_argument("--posfreq", type=float, default=1)
		self.command.add_argument("--rotfreq", type=float, default=1)
		self.command.add_argument("--ampl", nargs=3, type=float, default=None)
		self.command.add_argument("--rot", nargs=3, type=float, default=None)

	def run(self, args, sender):
		if args.ampl is None:
			args.ampl = Vector3.up
		else:
			args.ampl = Vector3(*args.ampl)
		if args.rot is None:
			args.rot = Vector3.up
		else:
			args.rot = Vector3(*args.rot)

		config = LDF()
		config.ldf_set("posFrequency", LDFDataType.FLOAT, args.posfreq)
		config.ldf_set("rotFrequency", LDFDataType.FLOAT, args.rotfreq)
		config.ldf_set("xAmplitude", LDFDataType.FLOAT, args.ampl.x)
		config.ldf_set("yAmplitude", LDFDataType.FLOAT, args.ampl.y)
		config.ldf_set("zAmplitude", LDFDataType.FLOAT, args.ampl.z)
		config.ldf_set("xRotation", LDFDataType.FLOAT, args.rot.x)
		config.ldf_set("yRotation", LDFDataType.FLOAT, args.rot.y)
		config.ldf_set("zRotation", LDFDataType.FLOAT, args.rot.z)
		sender.char.camera.add_camera_effect(config, effect_id="shake", effect_type="shake", duration=args.duration)

class CamReset(ChatCommand):
	def __init__(self):
		super().__init__("camreset")

	def run(self, args, sender):
		sender.char.remove_all_camera_effects()

class Freecam(ChatCommand):
	def __init__(self):
		super().__init__("freecam")
		self.command.add_argument("--off", action="store_true", default=False)

	def run(self, args, sender):
		if args.off:
			sender.char.camera.set_player_control_scheme(scheme=0)
		else:
			sender.char.camera.set_player_control_scheme(scheme=9)
