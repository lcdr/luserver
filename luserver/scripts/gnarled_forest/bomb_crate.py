import luserver.components.script as script
from luserver.components.mission import TaskType

MISSIONS = 333, 430, 431, 432, 454, 455, 456, 457, 458, 1427, 1525, 1562, 1599, 1627, 1637, 1647, 1657

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.physics.proximity_radius(20)
		self.players_near = 0

	def on_enter(self, player):
		self.players_near += 1
		self.object.render.play_animation("bounce")
		self.object.render.play_f_x_effect(name=b"bouncin", effect_type="anim")

	def on_exit(self, player):
		self.players_near -= 1
		if self.players_near < 1:
			self.object.render.play_animation("idle")
			self.object.render.stop_f_x_effect(name=b"bouncin")
			self.players_near = 0

	def on_hit(self, damage, attacker):
		# kill attacker if too close
		if attacker.physics.position.sq_distance(self.object.physics.position) < 10**2:
			attacker.destructible.simply_die(killer=self.object)

		# todo: originator=attacker
		self.object.skill.cast_skill(147)
		self.object.render.play_embedded_effect_on_all_clients_near_object(effect_name="camshake", from_object=self.object, radius=16)
		self.object.destructible.simply_die(killer=self.object)

		for mission_id in MISSIONS:
			attacker.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=mission_id)
