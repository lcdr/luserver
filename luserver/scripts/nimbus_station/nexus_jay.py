import luserver.components.script as script

JOIN_FACTION_MISSION_ID = 474

class ScriptComponent(script.ScriptComponent):
	def respond_to_mission(self, address, mission_id, player, reward_item):

		if mission_id != JOIN_FACTION_MISSION_ID:
			return

		if reward_item == 6980:
			achievements = [555, 556]
			flag_id = 46
			celebration_id = 14
		elif reward_item == 6979:
			achievements = [544, 545]
			flag_id = 47
			celebration_id = 15
		elif reward_item == 6981:
			achievements = [577, 578]
			flag_id = 48
			celebration_id = 16
		elif reward_item == 6978:
			achievements = [566, 567]
			flag_id = 49
			celebration_id = 17

		self._v_server.send_game_message(player.set_flag, True, flag_id, address=player.address)
		self._v_server.send_game_message(player.start_celebration_effect, animation="", duration=0, icon_id=0, main_text="", mixer_program="", music_cue="", path_node_name="", sound_guid="", sub_text="", celebration_id=celebration_id, address=player.address)

		achievements.append(778)
		player.add_mission(achievements[0]) # for some reason not an achievement, needs to be added manually

		for achievement_id in achievements:
			for mission in player.missions:
				if mission.id == achievement_id:
					mission.complete(self._v_server, player)
					break
