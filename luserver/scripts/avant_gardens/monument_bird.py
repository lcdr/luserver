import luserver.components.script as script

INTERACT_RADIUS = 10

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object._v_server.physics.add_with_radius(self.object, INTERACT_RADIUS)

	def on_enter(self, player):
		self.object.render.play_animation(animation_id="fly1", play_immediate=False)
		self.object.call_later(1, lambda: self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=player.object_id, loot_owner_id=0))

