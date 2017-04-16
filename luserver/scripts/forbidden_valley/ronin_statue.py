import luserver.components.script as script

INTERACT_RADIUS = 15
HATCH_TIME = 2

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.physics.proximity_radius(INTERACT_RADIUS)

	def on_enter(self, player):
		self.object.render.play_f_x_effect(name=b"dropdustmedium", effect_type="rebuild_medium", effect_id=2260)
		self.object.call_later(HATCH_TIME, self.hatch)
		self.object.skill.cast_skill(305)

	def hatch(self):
		self.object.render.play_f_x_effect(name=b"egg_puff_b", effect_type="create", effect_id=644)
		self.object._v_server.spawn_object(7815, {"position": self.object.physics.position, "rotation": self.object.physics.rotation})
		self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=0, loot_owner_id=0)
