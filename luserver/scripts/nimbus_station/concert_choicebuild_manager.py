import itertools

import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.index = self.object.groups[0][-1:]
		self.crate = None
		self.crates = [(11203, "Laser"), (11204, "Rocket"), (11205, "Speaker"), (11206, "Spotlight")]
		self.cycler = itertools.cycle(self.crates)
		self.spawn_crate()

	def spawn_crate(self) -> None:
		lot, group = next(self.cycler)
		self.crate = server.spawn_object(lot, {"position": self.object.physics.position, "rotation": self.object.physics.rotation, "spawn_group_on_smash": "Concert_"+group+"_QB_"+str(self.index)})
		self.crate.add_handler("death", self.crate_death)
		# seems like in the original implementation rockets have a shorter time of 3? but why?
		self.object.call_later(5, self.destroy_crate)

	def crate_death(self, *args, **kwargs):
		self.crate = None
		self.object.call_later(30, self.spawn_crate)

	def destroy_crate(self):
		if self.crate is not None:
			server.replica_manager.destruct(self.crate)
			self.crate = None
			self.spawn_crate()
