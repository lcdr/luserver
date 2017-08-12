from types import SimpleNamespace

import BTrees

from luserver.components.skill import BehaviorTemplate

class Init:
	def __init__(self, root, cdclient):
		self.root = root
		self.cdclient = cdclient

		root.factions = BTrees.IOBTree.BTree()
		for faction, enemyList in self.cdclient.execute("select faction, enemyList from Factions"):
			if not enemyList:
				enemies = ()
			else:
				enemies = tuple(int(i) for i in enemyList.split(","))
			root.factions[faction] = enemies

		root.object_skills = BTrees.IOBTree.BTree()
		for lot, skill_id, cast_on_type in self.cdclient.execute("select objectTemplate, skillID, castOnType from ObjectSkills"):
			root.object_skills.setdefault(lot, []).append((skill_id, cast_on_type))

		self.behavs_accessed = 0
		self.templates = {b: t for b, t in self.cdclient.execute("select behaviorID, templateID from BehaviorTemplate").fetchall()}
		self.parameters = {}
		for behavior_id, parameter_id, value in self.cdclient.execute("select behaviorID, parameterID, value from BehaviorParameter"):
			self.parameters.setdefault(behavior_id, {})[parameter_id] = value

		root.behavior = BTrees.IOBTree.BTree()
		root.skill_behavior = BTrees.IOBTree.BTree()
		for skill_id, behavior_id, imagination_cost in self.cdclient.execute("select skillID, behaviorID, imaginationcost from SkillBehavior"):
			root.skill_behavior[skill_id] = self.get_behavior(behavior_id), imagination_cost
		print("behavs_accessed", self.behavs_accessed)

	def get_behavior(self, behavior_id):
		if behavior_id == 0:
			return None
		behavior_id = int(behavior_id)
		if behavior_id not in self.root.behavior:
			self.behavs_accessed += 1
			if behavior_id not in self.templates:
				return None
			template_id = self.templates[behavior_id]
			params = self.parameters.get(behavior_id, {})
			self.root.behavior[behavior_id] = behavior = SimpleNamespace(id=behavior_id, template=template_id, **params)

			if template_id in (BehaviorTemplate.AreaOfEffect, BehaviorTemplate.OverTime, BehaviorTemplate.TargetCaster, BehaviorTemplate.Duration, BehaviorTemplate.AttackDelay, BehaviorTemplate.ChargeUp, BehaviorTemplate.Start, BehaviorTemplate.ClearTarget):
				behavior.action = self.get_behavior(behavior.action)

			if template_id == BehaviorTemplate.BasicAttack:
				if hasattr(behavior, "on_success"):
					if behavior.on_success == 0:
						del behavior.on_success
					else:
						behavior.on_success = self.get_behavior(behavior.on_success)
			elif template_id == BehaviorTemplate.TacArc:
				if hasattr(behavior, "action"):
					behavior.action = self.get_behavior(behavior.action)
				if hasattr(behavior, "blocked action"):
					behavior.blocked_action = self.get_behavior(getattr(behavior, "blocked action"))
					delattr(behavior, "blocked action")
				if hasattr(behavior, "miss action"):
					behavior.miss_action = self.get_behavior(getattr(behavior, "miss action"))
					delattr(behavior, "miss action")

			elif template_id == BehaviorTemplate.And:
				behavs = []
				for num in range(1, 11):
					if hasattr(behavior, "behavior %i" % num):
						behavs.append(self.get_behavior(getattr(behavior, "behavior %i" % num)))
						delattr(behavior, "behavior %i" % num)
				behavior.behaviors = tuple(behavs)

			elif template_id == BehaviorTemplate.ProjectileAttack:
				if hasattr(behavior, "spread_count"):
					behavior.spread_count = int(behavior.spread_count)
				behavior.projectile_lot = int(behavior.LOT_ID)
				del behavior.LOT_ID

			elif template_id == BehaviorTemplate.Heal:
				behavior.life = int(behavior.health)
				del behavior.health

			elif template_id == BehaviorTemplate.MovementSwitch:
				behavior.ground_action = self.get_behavior(behavior.ground_action)
				behavior.jump_action = self.get_behavior(behavior.jump_action)
				behavior.double_jump_action = self.get_behavior(behavior.double_jump_action)
				if hasattr(behavior, "air_action"):
					behavior.air_action = self.get_behavior(behavior.air_action)
				if hasattr(behavior, "falling_action"):
					behavior.falling_action = self.get_behavior(behavior.falling_action)
				if hasattr(behavior, "jetpack_action"):
					behavior.jetpack_action = self.get_behavior(behavior.jetpack_action)

			elif template_id == BehaviorTemplate.OverTime:
				behavior.num_intervals = int(behavior.num_intervals)

			elif template_id == BehaviorTemplate.Imagination:
				behavior.imagination = int(behavior.imagination)
			elif template_id == BehaviorTemplate.RepairArmor:
				behavior.armor = int(behavior.armor)

			elif template_id in (BehaviorTemplate.SpawnObject, BehaviorTemplate.SpawnQuickbuild):
				behavior.lot = int(behavior.LOT_ID)
				del behavior.LOT_ID

			elif template_id == BehaviorTemplate.Switch:
				behavior.action_true = self.get_behavior(behavior.action_true)
				behavior.action_false = self.get_behavior(behavior.action_false)
				if hasattr(behavior, "isEnemyFaction"):
					behavior.is_enemy_faction = behavior.isEnemyFaction
					del behavior.isEnemyFaction

			elif template_id == BehaviorTemplate.Buff:
				if hasattr(behavior, "life"):
					behavior.life = int(behavior.life)
				if hasattr(behavior, "armor"):
					behavior.armor = int(behavior.armor)
				if hasattr(behavior, "imag"):
					behavior.imagination = int(behavior.imag)
					del behavior.imag

			elif template_id == BehaviorTemplate.Jetpack:
				if hasattr(behavior, "warning_effect_id"):
					behavior.warning_effect_id = int(behavior.warning_effect_id)

			elif template_id == BehaviorTemplate.Chain:
				behavs = []
				for num in range(1, 5):
					if hasattr(behavior, "behavior %i" % num):
						behavs.append(self.get_behavior(getattr(behavior, "behavior %i" % num)))
						delattr(behavior, "behavior %i" % num)
				behavior.behaviors = tuple(behavs)

			elif template_id == BehaviorTemplate.ForceMovement:
				if hasattr(behavior, "hit_action"):
					behavior.hit_action = self.get_behavior(behavior.hit_action)
				if hasattr(behavior, "hit_action_enemy"):
					behavior.hit_action_enemy = self.get_behavior(behavior.hit_action_enemy)
				if hasattr(behavior, "hit_action_faction"):
					behavior.hit_action_faction = self.get_behavior(behavior.hit_action_faction)
				if hasattr(behavior, "timeout_action"):
					behavior.timeout_action = self.get_behavior(behavior.timeout_action)

			elif template_id == BehaviorTemplate.SwitchMultiple:
				behavs = []
				for num in range(1, 5):
					if hasattr(behavior, "behavior %i" % num):
						behavs.append((self.get_behavior(getattr(behavior, "behavior %i" % num)), getattr(behavior, "value %i" % num)))
						delattr(behavior, "behavior %i" % num)
						delattr(behavior, "value %i" % num)
				behavior.behaviors = tuple(behavs)

			elif template_id == BehaviorTemplate.NPCCombatSkill:
				if hasattr(behavior, "behavior"):
					behavior.behavior = self.get_behavior(behavior.behavior)
				elif hasattr(behavior, "behavior 1"):
					behavior.behavior = self.get_behavior(getattr(behavior, "behavior 1"))
					delattr(behavior, "behavior 1")
				if hasattr(behavior, "max range"):
					behavior.max_range = getattr(behavior, "max range")
					delattr(behavior, "max range")
				if hasattr(behavior, "min range"):
					behavior.min_range = getattr(behavior, "min range")
					delattr(behavior, "min range")

			elif template_id == BehaviorTemplate.Block:
				behavior.break_action = self.get_behavior(behavior.break_action)

			elif template_id == BehaviorTemplate.Verify:
				behavior.action = self.get_behavior(behavior.action)

			elif template_id == BehaviorTemplate.AirMovement:
				if hasattr(behavior, "ground_action"):
					behavior.ground_action = self.get_behavior(behavior.ground_action)
				if hasattr(behavior, "hit_action"):
					behavior.hit_action = self.get_behavior(behavior.hit_action)
				if hasattr(behavior, "hit_action_enemy"):
					behavior.hit_action_enemy = self.get_behavior(behavior.hit_action_enemy)
				if hasattr(behavior, "timeout_action"):
					behavior.timeout_action = self.get_behavior(behavior.timeout_action)

		return self.root.behavior[behavior_id]
