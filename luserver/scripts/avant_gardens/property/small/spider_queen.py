import luserver.components.script as script
from luserver.world import server
from luserver.math.quaternion import Quaternion

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.spiderlings_defeated = 0

	def on_destruction(self):
		server.world_control_object.script.on_spider_defeated()

	def on_hit(self, damage, attacker):
		if (self.object.stats.life > 222 and self.object.stats.life - damage <= 222) or (
		    self.object.stats.life > 111 and self.object.stats.life - damage <= 111):
			self.spiderlings_defeated = 0
			self.object.ai.disable()
			self.object.physics.rotation.update(Quaternion.identity)
			self.object.physics.attr_changed("rotation")
			self.object.render.play_animation("withdraw")
			self.object.call_later(3, self.object.render.play_animation, "idle-withdrawn")

			for egg in server.get_objects_in_group("SpiderEggs")[:2]:
				egg.script.spawn_spider()

	def spiderling_defeated(self):
		self.spiderlings_defeated += 1
		scream_sound = server.get_objects_in_group("Spider_Scream")[0]
		self.notify_client_object(name="EmitScream", param1=0, param2=0, param_str=b"", param_obj=scream_sound)

		if self.spiderlings_defeated == 2:
			self.object.ai.enable()
			self.object.render.play_animation("advance")
