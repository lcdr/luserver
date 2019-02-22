import logging
import pprint
from typing import Iterable, Optional, Sequence, Tuple

from bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint, c_ushort, ReadStream, WriteStream
from ..game_object import GameObject
from ..world import server
from ..math.vector import Vector3

log = logging.getLogger("luserver.components.skill")

class Behavior:
	def __init__(self, id: int):
		self.id = id

	def serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		log.debug("  " * level + type(self).__name__ + " %i", self.id)
		self._serialize(bitstream, caster, target, level)

	def deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		log.debug("  " * level + type(self).__name__ + " %i", self.id)
		if not isinstance(self, (DummyBehavior, BasicAttack, TacArc, And, Heal, MovementSwitch, AreaOfEffect, Imagination, TargetCaster, Stun, Duration, Knockback, AttackDelay, RepairArmor, Switch, SkillCastFailed, Chain, ForceMovement, ChargeUp, SwitchMultiple, Start, NPCCombatSkill, AirMovement)):
			log.debug(pprint.pformat(vars(self), indent=level))
		self._deserialize(bitstream, caster, target, level)

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		raise NotImplementedError

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		raise NotImplementedError

class DummyBehavior(Behavior):
	def __init__(self, id: int, template_id: int):
		super().__init__(id)
		self.template_id = template_id

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		log.debug("Template %i not implemented", self.template_id)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		log.debug("Template %i not implemented", self.template_id)

class BasicAttack(Behavior):
	def __init__(self, id: int, on_success: Optional[Behavior]):
		super().__init__(id)
		self.on_success = on_success

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.align_write()
		bitstream.write(c_ushort(0))
		bitstream.write(c_bit(False))
		bitstream.write(c_bit(False))
		bitstream.write(c_bit(True))
		bitstream.write(c_uint(0))
		damage = 1
		bitstream.write(c_uint(damage))
		aoe = False
		bitstream.write(c_bit(aoe))
		enemy_type = 1
		bitstream.write(c_ubyte(enemy_type))
		if self.on_success is not None:
			self.on_success.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.align_read()
		bitstream.read(c_ushort) # "padding", unused
		if target == caster:
			return
		assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)
		bitstream.read(c_bit) # usually False, but is True when using whirlwind scythe offhand skill (todo: investigate)
		log.debug(bitstream.read(c_uint))
		damage = bitstream.read(c_uint)
		log.debug(damage)
		log.debug("AoE? %s", bitstream.read(c_bit))
		enemy_type = bitstream.read(c_ubyte) # ?
		if enemy_type != 1:
			log.debug(enemy_type)
		log.debug(target)
		if target is not None:
			target.destructible.deal_damage(damage, caster)
		if self.on_success is not None:
			self.on_success.deserialize(bitstream, caster, target, level+1)

class TacArc(Behavior):
	def __init__(self, id: int, action: Optional[Behavior], blocked_action: Optional[Behavior], miss_action: Optional[Behavior], check_env: bool, use_picked_target: bool):
		super().__init__(id)
		self.action = action
		self.blocked_action = blocked_action
		self.miss_action = miss_action
		self.check_env = check_env
		self.use_picked_target = use_picked_target

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		is_hit = True
		bitstream.write(c_bit(is_hit))
		if self.check_env:
			is_blocked = False
			bitstream.write(c_bit(is_blocked))
		targets = [target]
		bitstream.write(c_uint(len(targets)))
		for target in targets:
			bitstream.write(c_int64(target.object_id))
		for target in targets:
			log.debug("Target %s", target)
			self.action.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.use_picked_target and caster.skill.picked_target_id != 0 and caster.skill.picked_target_id in server.game_objects:
			target = server.game_objects[caster.skill.picked_target_id]
			# todo: there seems to be a skill where this doesn't work and where the rest of the code should be executed as if the following lines weren't there?
			log.debug("using picked target, not completely working")
			self.action.deserialize(bitstream, caster, target, level+1)
			return
			# end of lines
		if bitstream.read(c_bit): # is hit
			if self.check_env:
				if bitstream.read(c_bit): # is blocked
					log.debug("hit but blocked")
					if self.blocked_action is not None:
						self.blocked_action.deserialize(bitstream, caster, target, level+1)
					return
			targets = []
			for _ in range(bitstream.read(c_uint)): # number of targets
				target_id = bitstream.read(c_int64)
				targets.append(server.game_objects.get(target_id))
			for target in targets:
				log.debug("Target %s", target)
				if self.action is not None:
					self.action.deserialize(bitstream, caster, target, level+1)

		else:
			if self.check_env:
				is_blocked = bitstream.read(c_bit)
				log.debug("blocked bit %s", is_blocked)
				if is_blocked:
					if self.blocked_action is None:
						log.error("TacArc would be blocked but has no blocked action!")
						return
					log.debug("blocked")
					self.blocked_action.deserialize(bitstream, caster, target, level+1)
					return
			if self.miss_action is not None:
				log.debug("miss")
				self.miss_action.deserialize(bitstream, caster, target, level+1)

class And(Behavior):
	def __init__(self, id: int, behavs: Iterable[Behavior]):
		super().__init__(id)
		self.behaviors = behavs

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		for behav in self.behaviors:
			behav.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		for behav in self.behaviors:
			behav.deserialize(bitstream, caster, target, level+1)

class ProjectileAttack(Behavior):
	def __init__(self, id: int, projectile_lot: int, spread_count: int):
		super().__init__(id)
		self.projectile_lot = projectile_lot
		self.spread_count = spread_count

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.write(c_int64(target.object_id))

		proj_behavs = []
		for skill_id, _ in server.db.object_skills[int(self.projectile_lot)]:
			proj_behavs.append(server.db.skill_behavior[skill_id][0])
		for _ in range(self.spread_count):
			bitstream.write(c_int64(caster.skill.cast_projectile(proj_behavs, target)))

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		target_id = bitstream.read(c_int64)
		if target_id != 0 and target_id in server.game_objects:
			target = server.game_objects[target_id]
			log.debug("target %s", target)

		proj_behavs = []
		for skill_id, _ in server.db.object_skills[int(self.projectile_lot)]:
			proj_behavs.append(server.db.skill_behavior[skill_id][0])

		for _ in range(self.spread_count):
			local_id = bitstream.read(c_int64)
			caster.skill.projectile_behaviors[local_id] = proj_behavs

class Heal(Behavior):
	def __init__(self, id: int, life: int):
		super().__init__(id)
		self.life = life

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		target.stats.life += self.life

class MovementType:
	Ground = 1
	Jump = 2
	Falling = 3
	DoubleJump = 4
	FallingAfterDoubleJumpAttack = 5
	Jetpack = 6
	Seven = 7  # FallingAfterHit / Knockback ?
	Nine = 9  # occurred with item 7311 - cutlass
	Rail = 10

class MovementSwitch(Behavior):
	def __init__(self, id: int, ground_action: Optional[Behavior], jump_action: Optional[Behavior], falling_action: Optional[Behavior], double_jump_action: Optional[Behavior], jetpack_action: Optional[Behavior]):
		super().__init__(id)
		self.ground_action = ground_action
		self.jump_action = jump_action
		self.falling_action = falling_action
		self.double_jump_action = double_jump_action
		self.jetpack_action = jetpack_action

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.write(c_uint(1))
		return

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		movement_type = bitstream.read(c_uint)
		log.debug("Movement type %i", movement_type)
		if movement_type in (MovementType.Ground, MovementType.Seven, MovementType.Nine, MovementType.Rail):
			action = self.ground_action
		elif movement_type == MovementType.Jump:
			action = self.jump_action
		elif movement_type in (MovementType.Falling, MovementType.FallingAfterDoubleJumpAttack):
			if self.falling_action is not None:
				action = self.falling_action
			else:
				action = self.ground_action
		elif movement_type == MovementType.DoubleJump:
			action = self.double_jump_action
		elif movement_type == MovementType.Jetpack:
			if self.jetpack_action is not None:
				action = self.jetpack_action
			else:
				action = self.ground_action
		else:
			raise NotImplementedError("Behavior", self.id, ": Movement type", movement_type)
		if action is not None:
			action.deserialize(bitstream, caster, target, level+1)

class AreaOfEffect(Behavior):
	def __init__(self, id: int, action: Optional[Behavior]):
		super().__init__(id)
		self.action = action

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.write(c_uint(0)) # number of targets

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		targets = []
		for _ in range(bitstream.read(c_uint)): # number of targets
			target_id = bitstream.read(c_int64)
			targets.append(server.game_objects[target_id])
		log.debug("targets: %s", targets)
		if self.action is not None:
			for target in targets:
				self.action.deserialize(bitstream, caster, target, level+1)

class OverTime(Behavior):
	def __init__(self, id: int, action: Behavior, num_intervals: int, delay: float):
		super().__init__(id)
		self.action = action
		self.num_intervals = num_intervals
		self.delay = delay

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		for interval in range(self.num_intervals):
			caster.call_later(interval * self.delay, self.action.deserialize, b"", caster, target, 0)

class Imagination(Behavior):
	def __init__(self, id: int, imag: int):
		super().__init__(id)
		self.imagination = imag

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		target.stats.imagination += self.imagination

class TargetCaster(Behavior):
	def __init__(self, id: int, action: Behavior):
		super().__init__(id)
		self.action = action

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		self.action.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		self.action.deserialize(bitstream, caster, target, level+1)

class Stun(Behavior):
	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		# needs to be researched more
		if False:#target.object_id != self.original_target_id:
			log.debug("Stun writing bit")
			bitstream.write(c_bit(False))

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if False:#target and target.object_id != self.original_target_id:
			log.debug("Stun reading bit")
			assert not bitstream.read(c_bit)

class Duration(Behavior):
	def __init__(self, id: int, action: Optional[Behavior], duration: float):
		super().__init__(id)
		self.action = action
		self.duration = duration

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.action is not None:
			self.action.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.action is not None:
			params = self.action.deserialize(bitstream, caster, target, level+1)
			caster.call_later(self.duration, caster.skill.undo_behavior, self.action, params)

class Knockback(Behavior):
	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.write(c_bit(False))

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		assert not bitstream.read(c_bit)

class AttackDelay(Behavior):
	def __init__(self, id: int, action: Optional[Behavior], delay: float):
		super().__init__(id)
		self.action = action
		self.delay = delay

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		handle = caster.skill.cast_sync_skill(self.delay, self.action, target)
		log.debug("write handle %s", handle)
		bitstream.write(c_uint(handle))

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		handle = bitstream.read(c_uint)
		log.debug("read handle %s", handle)
		caster.skill.delayed_behaviors[handle] = self.action

ChargeUp = AttackDelay # works the same

class RepairArmor(Behavior):
	def __init__(self, id: int, armor: int):
		super().__init__(id)
		self.armor = armor

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		target.stats.armor += self.armor

class SpawnObject(Behavior):
	def __init__(self, id: int, lot: int, distance: int):
		super().__init__(id)
		self.lot = lot
		self.distance = distance

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		position = caster.physics.position + caster.physics.rotation.rotate(Vector3.forward)*self.distance
		return server.spawn_object(self.lot, {"parent": caster, "position": position})

SpawnQuickbuild = SpawnObject # works the same

class Switch(Behavior):
	def __init__(self, id: int, action_false: Optional[Behavior], action_true: Optional[Behavior], imagination: int, is_enemy_faction: bool):
		super().__init__(id)
		self.action_false = action_false
		self.action_true = action_true
		self.imagination = imagination
		self.is_enemy_faction = is_enemy_faction

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		switch = True
		if self.imagination > 0 or not self.is_enemy_faction:
			log.debug("Switch writing bit")
			bitstream.write(c_bit(True))
		if switch:
			if self.action_true is not None:
				self.action_true.serialize(bitstream, caster, target, level+1)
		else:
			if self.action_false is not None:
				self.action_false.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		switch = True
		if self.imagination > 0 or not self.is_enemy_faction:
			log.debug("Switch reading bit")
			switch = bitstream.read(c_bit)
		if switch:
			if self.action_true is not None:
				self.action_true.deserialize(bitstream, caster, target, level+1)
		else:
			if self.action_false is not None:
				self.action_false.deserialize(bitstream, caster, target, level+1)

class Buff(Behavior):
	def __init__(self, id: int, life: int, armor: int, imagination: int):
		super().__init__(id)
		self.life = life
		self.armor = armor
		self.imagination = imagination

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		caster.stats.max_life += self.life
		caster.stats.max_armor += self.armor
		caster.stats.max_imagination += self.imagination

class Jetpack(Behavior):
	def __init__(self, id: int, bypass_checks: bool, enable_hover: bool, air_speed: float, max_air_speed: float, vertical_velocity: float, warning_effect_id: int):
		super().__init__(id)
		self.bypass_checks = bypass_checks
		self.enable_hover = enable_hover
		self.air_speed = air_speed
		self.max_air_speed = max_air_speed
		self.vertical_velocity = vertical_velocity
		self.warning_effect_id = warning_effect_id

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		caster.char.set_jet_pack_mode(self.bypass_checks, self.enable_hover, True, 167, self.air_speed, self.max_air_speed, self.vertical_velocity, self.warning_effect_id)

class SkillEvent(Behavior):
	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.id == 14211:
			event_name = "waterspray"
		elif self.id == 27031:
			event_name = "spinjitzu"
		else:
			event_name = None

		target.handle("skill_event", caster, event_name, silent=True)

class SkillCastFailed(Behavior):
	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		caster.skill.skill_cast_failed = True

class ApplyBuff(Behavior):
	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		pass

class Chain(Behavior):
	def __init__(self, id: int, behaviors: Sequence[Behavior]):
		super().__init__(id)
		self.behaviors = behaviors

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		chain_index = bitstream.read(c_uint)
		log.debug("chain index %i", chain_index)
		self.behaviors[chain_index-1].deserialize(bitstream, caster, target, level+1)

class ForceMovement(Behavior):
	def __init__(self, id: int, hit_action: Optional[Behavior], hit_action_enemy: Optional[Behavior], hit_action_faction: Optional[Behavior]):
		super().__init__(id)
		self.hit_action = hit_action
		self.hit_action_enemy = hit_action_enemy
		self.hit_action_faction = hit_action_faction

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.hit_action is not None or \
			 self.hit_action_enemy is not None or \
			 self.hit_action_faction is not None:
			handle = bitstream.read(c_uint)
			log.debug("move handle %s", handle)
			caster.skill.delayed_behaviors[handle] = None # not known yet

class Interrupt(Behavior):
	def __init__(self, id: int, interrupt_block: bool):
		super().__init__(id)
		self.interrupt_block = interrupt_block

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		if target != caster:
			log.debug("Interrupt: target != self, writing bit")
			bitstream.write(c_bit(False))
		if not self.interrupt_block:
			bitstream.write(c_bit(False))
		bitstream.write(c_bit(False))

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if target != caster:
			log.debug("Interrupt: target != self, reading bit")
			assert not bitstream.read(c_bit)
		if not self.interrupt_block:
			log.debug("Interrupt: not block, reading bit")
			assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)

class SwitchMultiple(Behavior):
	def __init__(self, id: int, behavs: Iterable[Tuple[Behavior, float]]):
		super().__init__(id)
		self.behaviors = behavs

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		charge_time = bitstream.read(c_float)
		for behav, value in self.behaviors:
			if charge_time <= value:
				behav.deserialize(bitstream, caster, target, level+1)
				break

class Start(Behavior):
	def __init__(self, id: int, action: Optional[Behavior]):
		super().__init__(id)
		self.action = action

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		if self.action is not None:
			self.action.deserialize(bitstream, caster, target, level+1)

class NPCCombatSkill(Behavior):
	def __init__(self, id: int, behavior: Behavior, min_range: int, max_range: int):
		super().__init__(id)
		self.behavior = behavior
		self.min_range = min_range
		self.max_range = max_range

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		self.behavior.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		self.behavior.deserialize(bitstream, caster, target, level+1)

class Verify(Behavior):
	def __init__(self, id: int, action: Behavior):
		super().__init__(id)
		self.action = action

	def _serialize(self, bitstream: WriteStream, caster: GameObject, target: GameObject, level: int) -> None:
		bitstream.write(c_bit(False))
		bitstream.write(c_uint(0))
		bitstream.write(c_bit(False)) # blocking
		bitstream.write(c_bit(False)) # charging
		self.action.serialize(bitstream, caster, target, level+1)

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		assert not bitstream.read(c_bit)
		assert bitstream.read(c_uint) == 0
		assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)
		self.action.deserialize(bitstream, caster, target, level+1)

class AirMovement(Behavior):
	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		handle = bitstream.read(c_uint)
		log.debug("move handle %s", handle)
		caster.skill.delayed_behaviors[handle] = None # not known yet

class ClearTarget(Behavior):
	def __init__(self, id: int, action: Behavior):
		super().__init__(id)
		self.action = action

	def _deserialize(self, bitstream: ReadStream, caster: GameObject, target: GameObject, level: int) -> None:
		self.action.deserialize(bitstream, caster, target, level+1)
