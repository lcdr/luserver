import luserver.components.script as script
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		rewards = server.db.activity_rewards[self.object.scripted_activity.comp_id]
		self.object.physics.drop_rewards(*rewards, player)
