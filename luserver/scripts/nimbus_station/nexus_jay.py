import luserver.components.script as script

JOIN_FACTION_MISSION_ID = 474

SENTINEL_COMMENDATION = 6978
ASSEMBLY_COMMENDATION = 6979
VENTURE_LEAGUE_COMMENDATION = 6980
PARADOX_COMMENDATION = 6981

VENTURE_LEAGUE_FLAG = 46
ASSEMBLY_FLAG = 47
PARADOX_FLAG = 48
SENTINEL_FLAG = 49

class ScriptComponent(script.ScriptComponent):
	def respond_to_mission(self, mission_id, player, reward_item):
		if mission_id != JOIN_FACTION_MISSION_ID:
			return

		if reward_item == VENTURE_LEAGUE_COMMENDATION:
			achievements = [555, 556]
			flag_id = VENTURE_LEAGUE_FLAG
			celebration_id = 14
		elif reward_item == ASSEMBLY_COMMENDATION:
			achievements = [544, 545]
			flag_id = ASSEMBLY_FLAG
			celebration_id = 15
		elif reward_item == PARADOX_COMMENDATION:
			achievements = [577, 578]
			flag_id = PARADOX_FLAG
			celebration_id = 16
		elif reward_item == SENTINEL_COMMENDATION:
			achievements = [566, 567]
			flag_id = SENTINEL_FLAG
			celebration_id = 17
		else:
			raise ValueError

		player.char.set_flag(True, flag_id)
		player.char.start_celebration_effect(animation="", duration=0, icon_id=0, main_text="", mixer_program=b"", music_cue=b"", path_node_name=b"", sound_guid=b"", sub_text="", celebration_id=celebration_id)

		achievements.append(778)
		player.char.add_mission(achievements[0]) # for some reason not an achievement, needs to be added manually

		for achievement_id in achievements:
			player.char.complete_mission(achievement_id)
