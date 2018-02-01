import enum
import logging
import pprint
from typing import Dict

from pyraknet.bitstream import c_bit, c_uint, c_uint64, ReadStream, WriteStream
from ..game_object import broadcast, c_int, c_int64, E, GameObject, ObjectID, single
from ..game_object import c_uint as c_uint_
from ..world import server
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType, ItemType, Stack
from .mission import TaskType
from .behaviors import BasicAttack, TacArc, And, ProjectileAttack, Heal, MovementSwitch, AreaOfEffect, OverTime, Imagination, TargetCaster, Stun, Duration, Knockback, AttackDelay, RepairArmor, SpawnObject, Switch, Buff, Jetpack, SkillEvent, SkillCastFailed, Chain, ForceMovement, Interrupt, ChargeUp, SwitchMultiple, Start, NPCCombatSkill, Verify, AirMovement, SpawnQuickbuild, ClearTarget

log = logging.getLogger(__name__)

class BehaviorTemplate(enum.IntEnum):
	BasicAttack = 1
	TacArc = 2
	And = 3
	ProjectileAttack = 4
	Heal = 5
	MovementSwitch = 6
	AreaOfEffect = 7
	PlayEffect = 8
	Immunity = 9
	DamageBuff = 10
	DamageAbsorption = 11
	OverTime = 12
	Imagination = 13
	TargetCaster = 14
	Stun = 15
	Duration = 16
	Knockback = 17
	AttackDelay = 18
	CarBoost = 19
	FallSpeed = 20
	Shield = 21
	RepairArmor = 22
	Speed = 23
	DarkInspiration = 24
	LootBuff = 25
	VentureVision = 26
	SpawnObject = 27
	LayBrick = 28
	Switch = 29
	Buff = 30
	Jetpack = 31
	SkillEvent = 32
	ConsumeItem = 33
	SkillCastFailed = 34
	ImitationSkunkStink = 35
	ChangeIdleFlags = 36
	ApplyBuff = 37
	Chain = 38
	ChangeOrientation = 39
	ForceMovement = 40
	Interrupt = 41
	AlterCooldown = 42
	ChargeUp = 43
	SwitchMultiple = 44
	Start = 45
	End = 46
	AlterChainDelay = 47
	Camera = 48
	RemoveBuff = 49
	Grab = 50
	ModularBuild = 51
	NPCCombatSkill = 52
	Block = 53
	Verify = 54
	Taunt = 55
	AirMovement = 56
	SpawnQuickbuild = 57
	PullToPoint = 58
	PropertyRotate = 59
	DamageReduction = 60
	PropertyTeleport = 61
	ClearTarget = 62
	TakePicture = 63
	Mount = 64
	SkillSet = 65

TEMPLATES = {
	BehaviorTemplate.BasicAttack: BasicAttack,
	BehaviorTemplate.TacArc: TacArc,
	BehaviorTemplate.And: And,
	BehaviorTemplate.ProjectileAttack: ProjectileAttack,
	BehaviorTemplate.Heal: Heal,
	BehaviorTemplate.MovementSwitch: MovementSwitch,
	BehaviorTemplate.AreaOfEffect: AreaOfEffect,
	BehaviorTemplate.OverTime: OverTime,
	BehaviorTemplate.Imagination: Imagination,
	BehaviorTemplate.TargetCaster: TargetCaster,
	BehaviorTemplate.Stun: Stun,
	BehaviorTemplate.Duration: Duration,
	BehaviorTemplate.Knockback: Knockback,
	BehaviorTemplate.AttackDelay: AttackDelay,
	BehaviorTemplate.RepairArmor: RepairArmor,
	BehaviorTemplate.SpawnObject: SpawnObject,
	BehaviorTemplate.Switch: Switch,
	BehaviorTemplate.Buff: Buff,
	BehaviorTemplate.Jetpack: Jetpack,
	BehaviorTemplate.SkillEvent: SkillEvent,
	BehaviorTemplate.SkillCastFailed: SkillCastFailed,
	BehaviorTemplate.Chain: Chain,
	BehaviorTemplate.ForceMovement: ForceMovement,
	BehaviorTemplate.Interrupt: Interrupt,
	BehaviorTemplate.ChargeUp: ChargeUp,
	BehaviorTemplate.SwitchMultiple: SwitchMultiple,
	BehaviorTemplate.Start: Start,
	BehaviorTemplate.NPCCombatSkill: NPCCombatSkill,
	BehaviorTemplate.Verify: Verify,
	BehaviorTemplate.AirMovement: AirMovement,
	BehaviorTemplate.SpawnQuickbuild: SpawnQuickbuild,
	BehaviorTemplate.ClearTarget: ClearTarget}

class SkillSlot:
	RightHand = 0
	LeftHand = 1
	Neck = 2
	Hat = 3

class CastType:
	AddSkill = 0
	Cast = 1
	Two = 2 # not sure, but i'll use this for casts
	Consumable = 3
	EverlastingConsumable = 4

PASSIVE_BEHAVIORS = BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.Jetpack, BehaviorTemplate.SkillCastFailed, BehaviorTemplate.ApplyBuff

class SkillComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Dict[str, object], comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.skill = self
		self.delayed_behaviors = {}
		self.projectile_behaviors = {}
		self.original_target_id = None
		self.last_ui_handle = 0
		self.last_ui_skill_handle = self.last_ui_handle
		self.skill_cast_failed = False
		self.everlasting = False
		self.skills = [skill_id for skill_id, _ in server.db.object_skills.get(self.object.lot, [])]

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if is_creation:
			out.write(c_bit(False))

	def on_destruction(self) -> None:
		self.delayed_behaviors.clear()
		self.projectile_behaviors.clear()

	def cast_skill(self, skill_id: int, target: GameObject=None, cast_type: int=CastType.Two) -> None:
		if target is None:
			target = self.object
		self.original_target_id = target.object_id

		self.last_ui_skill_handle = self.last_ui_handle
		self.last_ui_handle += 1

		bitstream = WriteStream()
		behavior = server.db.skill_behavior[skill_id][0]
		self.serialize_behavior(behavior, bitstream, target)
		self.start_skill(skill_id=skill_id, cast_type=cast_type, optional_target_id=target.object_id, ui_skill_handle=self.last_ui_skill_handle, optional_originator_id=0, originator_rot=Quaternion(0, 0, 0, 0), bitstream=bytes(bitstream))

	def cast_sync_skill(self, delay: float, behavior, target: GameObject) -> int:
		ui_behavior_handle = self.last_ui_handle
		self.last_ui_handle += 1
		self.delayed_behaviors[ui_behavior_handle] = behavior

		bitstream = WriteStream()
		self.serialize_behavior(behavior, bitstream, target)

		self.object.call_later(delay, lambda: self.sync_skill(bitstream=bytes(bitstream), ui_behavior_handle=ui_behavior_handle, ui_skill_handle=self.last_ui_skill_handle))
		return ui_behavior_handle

	def cast_projectile(self, proj_behavs, target: GameObject) -> ObjectID:
		bitstream = WriteStream()
		proj_id = server.new_spawned_id()
		for behav in proj_behavs:
			self.original_target_id = target.object_id
			self.serialize_behavior(behav, bitstream, target)
		delay = 1
		self.object.call_later(delay, lambda: self.request_server_projectile_impact(proj_id, target.object_id, bytes(bitstream)))
		return proj_id

	@broadcast
	def echo_start_skill(self, used_mouse:bool=False, caster_latency:float=0, cast_type:c_int=0, last_clicked_posit:Vector3=Vector3.zero, optional_originator_id:c_int64=E, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:bytes=E, skill_id:c_uint_=E, ui_skill_handle:c_uint_=0) -> None:
		pass

	def start_skill(self, used_mouse:bool=False, consumable_item_id:c_int64=0, caster_latency:float=0, cast_type:c_int=0, last_clicked_posit:Vector3=Vector3.zero, optional_originator_id:c_int64=E, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:bytes=E, skill_id:c_uint_=E, ui_skill_handle:c_uint_=0) -> None:
		assert not used_mouse
		assert caster_latency == 0
		assert last_clicked_posit == Vector3.zero
		assert optional_originator_id in (0, self.object.object_id)
		assert originator_rot == Quaternion(0, 0, 0, 0)

		if cast_type in (CastType.Cast, CastType.Two): # casts?
			player = None # send to all including self
		else:
			player = self.object # exclude self

		self.echo_start_skill(used_mouse, caster_latency, cast_type, last_clicked_posit, optional_originator_id, optional_target_id, originator_rot, bitstream, skill_id, ui_skill_handle, player=player)

		stream = ReadStream(bitstream)

		if hasattr(self.object, "char"):
			self.object.char.update_mission_task(TaskType.UseSkill, None, skill_id)

		if optional_target_id != 0:
			if optional_target_id not in server.game_objects:
				return
			target = server.game_objects[optional_target_id]#self.object
		else:
			target = self.object
		self.picked_target_id = optional_target_id
		behavior, imagination_cost = server.db.skill_behavior[skill_id]
		self.original_target_id = target.object_id
		self.skill_cast_failed = False
		self.deserialize_behavior(behavior, stream, target)
		if not self.skill_cast_failed:
			self.object.stats.imagination -= imagination_cost

		if not stream.all_read():
			log.warning("not all read, remaining: %s", stream.read_remaining())

		# remove consumable
		if not self.everlasting and consumable_item_id != 0 and cast_type == CastType.Consumable:
			self.object.inventory.remove_item(InventoryType.Items, object_id=consumable_item_id)

	def select_skill(self, from_skill_set:bool=False, skill_id:c_int=E) -> None:
		pass

	@broadcast
	def add_skill(self, ai_combat_weight:c_int=0, from_skill_set:bool=False, cast_type:c_int=0, time_secs:float=-1, times_can_cast:c_int=-1, skill_id:c_uint_=E, slot_id:c_int=-1, temporary:bool=True) -> None:
		pass

	@single
	def remove_skill(self, from_skill_set:bool=False, skill_id:c_uint_=E) -> None:
		pass

	@broadcast
	def echo_sync_skill(self, done:bool=False, bitstream:bytes=E, ui_behavior_handle:c_uint_=E, ui_skill_handle:c_uint_=E) -> None:
		pass

	def sync_skill(self, done:bool=False, bitstream:bytes=E, ui_behavior_handle:c_uint_=E, ui_skill_handle:c_uint_=E) -> None:
		if hasattr(self.object, "char"):
			player = self.object
		else:
			player = None
		self.echo_sync_skill(done, bitstream, ui_behavior_handle, ui_skill_handle, player=player) # don't send echo to self
		if ui_behavior_handle not in self.delayed_behaviors:
			log.error("Handle %i not handled!", ui_behavior_handle)
			return
		stream = ReadStream(bitstream)
		behavior = self.delayed_behaviors[ui_behavior_handle]
		target = self.object
		if behavior is None:
			behavior_id = stream.read(c_uint)
			target_id = stream.read(c_uint64)
			if behavior_id != 0:
				behavior = server.db.behavior[behavior_id]
			if target_id != 0:
				target = server.game_objects[target_id]

		if behavior is not None: # no, this is not an "else" from above
			self.original_target_id = target.object_id
			self.deserialize_behavior(behavior, stream, target)
		if not stream.all_read():
			log.warning("not all read, remaining: %s", stream.read_remaining())
		if done:
			del self.delayed_behaviors[ui_behavior_handle]

	def request_server_projectile_impact(self, local_id:c_int64=0, target_id:c_int64=0, bitstream:bytes=E) -> None:
		stream = ReadStream(bitstream)
		if target_id == 0:
			target = self.object
		else:
			if target_id not in server.game_objects:
				log.debug("Projectile Target %i not in game objects", target_id)
				return
			target = server.game_objects[target_id]

		if local_id not in self.projectile_behaviors:
			log.warning("Projectile ID %i not in behavior list, it's likely a previous behavior did not parse correctly", local_id)
			return

		for behav in self.projectile_behaviors[local_id]:
			self.original_target_id = target.object_id
			self.deserialize_behavior(behav, stream, target)
		del self.projectile_behaviors[local_id]
		# todo: do client projectile impact

	def serialize_behavior(self, behavior, bitstream: WriteStream, target: GameObject, level=0):
		log.debug("  "*level+BehaviorTemplate(behavior.template).name+" %i", behavior.id)
		if behavior.template in TEMPLATES:
			return TEMPLATES[behavior.template].serialize(self, behavior, bitstream, target, level)

	def deserialize_behavior(self, behavior, bitstream: ReadStream, target: GameObject, level=0) -> None:
		if behavior is None:
			return
		log.debug("  "*level+BehaviorTemplate(behavior.template).name+" %i", behavior.id)
		if behavior.template not in (BehaviorTemplate.BasicAttack, BehaviorTemplate.TacArc, BehaviorTemplate.And, BehaviorTemplate.Heal, BehaviorTemplate.MovementSwitch, BehaviorTemplate.AreaOfEffect, BehaviorTemplate.PlayEffect, BehaviorTemplate.Imagination, BehaviorTemplate.TargetCaster, BehaviorTemplate.Stun, BehaviorTemplate.Duration, BehaviorTemplate.Knockback, BehaviorTemplate.AttackDelay, BehaviorTemplate.RepairArmor, BehaviorTemplate.Switch, BehaviorTemplate.SkillCastFailed, BehaviorTemplate.Chain, BehaviorTemplate.ChangeOrientation, BehaviorTemplate.ForceMovement, BehaviorTemplate.AlterCooldown, BehaviorTemplate.ChargeUp, BehaviorTemplate.SwitchMultiple, BehaviorTemplate.Start, BehaviorTemplate.AlterChainDelay, BehaviorTemplate.NPCCombatSkill, BehaviorTemplate.AirMovement):
			log.debug(pprint.pformat(vars(behavior), indent=level))

		if behavior.template in TEMPLATES:
			TEMPLATES[behavior.template].deserialize(self, behavior, bitstream, target, level)

	def undo_behavior(self, behavior, params=None) -> None:
		if behavior.template == BehaviorTemplate.SpawnObject:
			server.replica_manager.destruct(params)
		elif behavior.template == BehaviorTemplate.Buff:
			if hasattr(behavior, "life"):
				self.object.stats.max_life -= behavior.life
			if hasattr(behavior, "armor"):
				self.object.stats.max_armor -= behavior.armor
			if hasattr(behavior, "imagination"):
				self.object.stats.max_imagination -= behavior.imagination
		elif behavior.template == BehaviorTemplate.Jetpack:
			self.object.char.set_jet_pack_mode(enable=False)

	def add_skill_for_item(self, item: Stack, add_buffs=True) -> None:
		if item.lot in server.db.object_skills:
			for skill_id, cast_on_type in server.db.object_skills[item.lot]:
				behavior = server.db.skill_behavior[skill_id][0]
				if cast_on_type == CastType.AddSkill:
					slot_id = SkillSlot.RightHand
					if item.item_type == ItemType.Hat:
						slot_id = SkillSlot.Hat
					elif item.item_type == ItemType.LeftHand:
						slot_id = SkillSlot.LeftHand
					elif item.item_type == ItemType.Neck:
						slot_id = SkillSlot.Neck
					self.add_skill(skill_id=skill_id, slot_id=slot_id)
				elif cast_on_type == CastType.Cast and add_buffs:
					self.cast_skill(skill_id, cast_type=CastType.Cast)

	def add_skill_server(self, skill_id: int) -> None:
		self.cast_skill(skill_id, cast_type=CastType.Cast)

	def remove_skill_for_item(self, item: Stack) -> None:
		if item.lot in server.db.object_skills:
			for skill_id, cast_on_type in server.db.object_skills[item.lot]:
				behavior = server.db.skill_behavior[skill_id][0]
				if behavior.template in PASSIVE_BEHAVIORS:
					assert cast_on_type == 1
					self.undo_behavior(behavior)
				elif cast_on_type == CastType.AddSkill:
					self.remove_skill(skill_id=skill_id)

	def remove_skill_server(self, skill_id: int) -> None:
		behavior = server.db.skill_behavior[skill_id][0]
		if behavior.template in PASSIVE_BEHAVIORS:
			self.undo_behavior(behavior)
