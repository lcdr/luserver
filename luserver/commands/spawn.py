from ..world import server
from ..components.physics import PhysicsEffect
from ..math.vector import Vector3
from .command import ChatCommand

class DestroySpawned(ChatCommand):
	def __init__(self):
		super().__init__("destroyspawned")

	def run(self, args, sender):
		for child in sender.children.copy():
			server.replica_manager.destruct(server.game_objects[child])

class Spawn(ChatCommand):
	def __init__(self):
		super().__init__("spawn", description="Spawn an object")
		self.command.add_argument("lot", type=int)
		self.command.add_argument("--position", nargs=3, type=float)
		self.command.add_argument("--name", nargs="+")

	def run(self, args, sender):
		set_vars = {"parent": sender}
		if args.position is not None:
			set_vars["position"] = args.position
		if args.name is not None:
			set_vars["name"] = " ".join(args.name)
		server.spawn_object(args.lot, set_vars)

class SpawnPhantom(ChatCommand):
	def __init__(self):
		super().__init__("spawnphantom")
		self.command.add_argument("--type", choices=("wall", "cube"), default="cube")
		self.command.add_argument("--effect", choices=("push", "attract", "repulse", "gravity", "friction"), default="push")
		self.command.add_argument("--amount", type=float, default=500)
		self.command.add_argument("--direction", nargs=3, type=float, default=Vector3.up)
		self.command.add_argument("--scale", type=float, default=1)

	def run(self, args, sender):
		if args.type == "wall":
			lot = 4734
			displacement = Vector3()
		elif args.type == "cube":
			lot = 5652
			displacement = Vector3(0, 2.5, 0)
		if not isinstance(args.direction, Vector3):
			args.direction = Vector3(args.direction)
		set_vars = {
			"scale": args.scale,
			"parent": sender,
			"position": sender.physics.position+displacement}
		obj = server.spawn_object(lot, set_vars)
		obj.physics.physics_effect_active = True
		obj.physics.physics_effect_type = PhysicsEffect[args.effect.title()]
		obj.physics.physics_effect_amount = args.amount
		obj.physics.physics_effect_direction = args.direction*args.amount
