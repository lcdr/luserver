import BTrees

from luserver.components.behaviors import And, AreaOfEffect, AttackDelay, Behavior, BasicAttack, Buff, Chain, ClearTarget, Duration, ForceMovement, Heal, Imagination, Interrupt, Jetpack, Knockback, MovementSwitch, NPCCombatSkill, OverTime, ProjectileAttack, RepairArmor, SkillCastFailed, SkillEvent, SpawnObject, Start, Stun, Switch, SwitchMultiple, TacArc, TargetCaster, Verify
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
		if behavior_id not in self.templates:
			return None
		if behavior_id in self.root.behavior:
			return self.root.behavior[behavior_id]
		self.behavs_accessed += 1
		template_id = self.templates[behavior_id]
		params = self.parameters.get(behavior_id, {})

		if template_id == BehaviorTemplate.BasicAttack:
			if "on_success" in params:
				on_success = self.get_behavior(params["on_success"])
			else:
				on_success = None
			behavior = BasicAttack(behavior_id, on_success)

		elif template_id == BehaviorTemplate.TacArc:
			if "action" in params:
				action = self.get_behavior(params["action"])
			else:
				action = None
			if "blocked action" in params:
				blocked_action = self.get_behavior(params["blocked action"])
			else:
				blocked_action = None
			if "miss action" in params:
				miss_action = self.get_behavior(params["miss action"])
			else:
				miss_action = None
			if "check_env" in params:
				check_env = params["check_env"]
			else:
				check_env = False
			if "use_picked_target" in params:
				use_picked_target = params["use_picked_target"]
			else:
				use_picked_target = False
			behavior = TacArc(behavior_id, action, blocked_action, miss_action, check_env, use_picked_target)

		elif template_id == BehaviorTemplate.And:
			behavs = []
			for num in range(1, 11):
				if "behavior %i" % num:
					behavs.append(self.get_behavior(params["behavior %i" % num]))
			behavior = And(behavior_id, behavs)

		elif template_id == BehaviorTemplate.ProjectileAttack:
			if "spread_count" in params and params["spread_count"] != 0:
				spread_count = params["spread_count"]
			else:
				spread_count = 1
			behavior = ProjectileAttack(behavior_id, params["LOT_ID"], spread_count)
		elif template_id == BehaviorTemplate.Heal:
			life = int(params["health"])
			behavior = Heal(behavior_id, life)

		elif template_id == BehaviorTemplate.MovementSwitch:
			if "ground_action" in params:
				ground_action = self.get_behavior(params["ground_action"])
			else:
				ground_action = None
			if "jump_action" in params:
				jump_action = self.get_behavior(params["jump_action"])
			else:
				jump_action = None
			if "falling_action" in params:
				falling_action = self.get_behavior(params["falling_action"])
			else:
				falling_action = None
			double_jump_action = self.get_behavior(params["double_jump_action"])
			if "jetpack_action" in params:
				jetpack_action = self.get_behavior(params["jetpack_action"])
			else:
				jetpack_action = None
			behavior = MovementSwitch(behavior_id, ground_action, jump_action, falling_action, double_jump_action, jetpack_action)

		elif template_id == BehaviorTemplate.AreaOfEffect:
			if "action" in params:
				action = self.get_behavior(params["action"])
			else:
				action = None
			behavior = AreaOfEffect(behavior_id, action)

		elif template_id in (BehaviorTemplate.PlayEffect, BehaviorTemplate.Immunity, BehaviorTemplate.DamageBuff, BehaviorTemplate.DamageAbsorption):
			behavior = Behavior(behavior_id)

		elif template_id == BehaviorTemplate.OverTime:
			behavior = OverTime(behavior_id, self.get_behavior(params["action"]), int(params["num_parameters"]), params["delay"])

		elif template_id == BehaviorTemplate.Imagination:
			behavior = Imagination(behavior_id, int(params["imagination"]))

		elif template_id == BehaviorTemplate.TargetCaster:
			behavior = TargetCaster(behavior_id, self.get_behavior(params["action"]))

		elif template_id == BehaviorTemplate.Stun:
			behavior = Stun(behavior_id)

		elif template_id == BehaviorTemplate.Duration:
			if "action" in params:
				action = self.get_behavior(params["action"])
			else:
				action = None
			if "duration" in params:
				duration = params["duration"]
			else:
				duration = params["delay"]
			behavior = Duration(behavior_id, action, duration)

		elif template_id == BehaviorTemplate.Knockback:
			behavior = Knockback(behavior_id)

		elif template_id == BehaviorTemplate.AttackDelay:
			behavior = AttackDelay(behavior_id, self.get_behavior(params["action"]), params["delay"])

		elif template_id == BehaviorTemplate.RepairArmor:
			behavior = RepairArmor(behavior_id, int(params["armor"]))

		elif template_id == BehaviorTemplate.SpawnObject:
			behavior = SpawnObject(behavior_id, int(params["LOT_ID"]), params.get("distance", 0))

		elif template_id == BehaviorTemplate.Switch:
			if "action_true" in params:
				action_true = self.get_behavior(params["action_true"])
			else:
				action_true = None
			behavior = Switch(behavior_id, self.get_behavior(params["action_false"]), action_true, params.get("imagination", 0), params.get("isEnemyFaction", False))

		elif template_id == BehaviorTemplate.Buff:
			behavior = Buff(behavior_id, int(params.get("life", 0)), int(params.get("armor", 0)), int(params.get("imag", 0)))

		elif template_id == BehaviorTemplate.Jetpack:
			behavior = Jetpack(behavior_id, params.get("bypass_checks", True), params.get("enable_hover", False), params.get("air_speed", 10), params.get("max_air_speed", 15), params.get("vertical_velocity", 1), int(params.get("warning_effect_id", -1)))

		elif template_id == BehaviorTemplate.SkillEvent:
			behavior = SkillEvent(behavior_id)

		elif template_id == BehaviorTemplate.SkillCastFailed:
			behavior = SkillCastFailed(behavior_id)

		elif template_id == BehaviorTemplate.Chain:
			behavs = []
			for num in range(1, 5):
				if "behavior %i" % num in params:
					behavs.append(self.get_behavior(params["behavior %i" % num]))
			behavior = Chain(behavior_id, behavs)

		elif template_id == BehaviorTemplate.ForceMovement:
			if "hit_action" in params:
				hit_action = self.get_behavior(params["hit_action"])
			else:
				hit_action = None
			if "hit_action_enemy" in params:
				hit_action_enemy = self.get_behavior(params["hit_action_enemy"])
			else:
				hit_action_enemy = None
			if "hit_action_faction" in params:
				hit_action_faction = self.get_behavior(params["hit_action_faction"])
			else:
				hit_action_faction = None
			behavior = ForceMovement(behavior_id, hit_action, hit_action_enemy, hit_action_faction)

		elif template_id == BehaviorTemplate.Interrupt:
			behavior = Interrupt(behavior_id, params.get("interrupt_block", False))

		elif template_id == BehaviorTemplate.SwitchMultiple:
			behavs = []
			for num in range(1, 5):
				if "behavior %i" % num in params:
					behavs.append((self.get_behavior(params["behavior %i" % num]), params["value %i" % num]))

			behavior = SwitchMultiple(behavior_id, behavs)

		elif template_id == BehaviorTemplate.Start:
			behavior = Start(behavior_id, self.get_behavior(params["action"]))

		elif template_id == BehaviorTemplate.NPCCombatSkill:
			if "behavior" in params:
				behav = self.get_behavior(params["behavior"])
			elif "behavior 1" in params:
				behav = self.get_behavior(params["behavior 1"])
			else:
				raise ValueError
			behavior = NPCCombatSkill(behavior_id, behav)

		elif template_id == BehaviorTemplate.Verify:
			behavior = Verify(behavior_id, self.get_behavior(params["action"]))

		elif template_id == BehaviorTemplate.ClearTarget:
			behavior = ClearTarget(behavior_id, self.get_behavior(params["action"]))
		else:
			raise ValueError(template_id)

		"""
		
		elif template_id == BehaviorTemplate.Block:
			behavior.break_action = self.get_behavior(behavior.break_action)

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
	"""
