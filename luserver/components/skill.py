import logging
import pprint
import enum

from ..bitstream import BitStream, c_bit, c_int, c_int64, c_uint, c_uint64
from ..messages import broadcast, single
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType, ItemType
from .mission import TaskType
from .behaviors import BasicAttack, TacArc, And, ProjectileAttack, Heal, MovementSwitch, AreaOfEffect, OverTime, Imagination, TargetCaster, Stun, Duration, Knockback, AttackDelay, RepairArmor, SpawnObject, Switch, Buff, Jetpack, SkillEvent, Chain, ForceMovement, Interrupt, ChargeUp, SwitchMultiple, Start, NPCCombatSkill, Verify, AirMovement, SpawnQuickbuild, ClearTarget

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
	Two = 2 # not sure, but i'll use this for casts
	Consumable = 3
	EverlastingConsumable = 4

PASSIVE_BEHAVIORS = BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.Jetpack, BehaviorTemplate.SkillCastFailed, BehaviorTemplate.ApplyBuff

class SkillComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.skill = self
		self.delayed_behaviors = {}
		self.projectile_behaviors = {}
		self.original_target_id = None
		self.last_ui_handle = 0
		self.last_ui_skill_handle = self.last_ui_handle
		self.everlasting = False
		self.skills = self.object._v_server.db.object_skills.get(self.object.lot, []).copy()

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))

	def on_destruction(self):
		self.delayed_behaviors.clear()
		self.projectile_behaviors.clear()

	def cast_skill(self, skill_id, target=None):
		if target is None:
			target = self.object
		self.original_target_id = target.object_id

		self.last_ui_skill_handle = self.last_ui_handle
		self.last_ui_handle += 1

		bitstream = BitStream()
		behavior = self.object._v_server.db.skill_behavior[skill_id][0]
		self.serialize_behavior(behavior, bitstream, target)
		self.start_skill(skill_id=skill_id, cast_type=CastType.Two, optional_target_id=target.object_id, ui_skill_handle=self.last_ui_skill_handle, optional_originator_id=0, originator_rot=Quaternion(0, 0, 0, 0), bitstream=bitstream)

	def cast_sync_skill(self, delay, behavior, target):
		ui_behavior_handle = self.last_ui_handle
		self.last_ui_handle += 1
		self.delayed_behaviors[ui_behavior_handle] = behavior

		bitstream = BitStream()
		self.serialize_behavior(behavior, bitstream, target)

		self.object.call_later(delay, lambda: self.sync_skill(bitstream=bitstream, ui_behavior_handle=ui_behavior_handle, ui_skill_handle=self.last_ui_skill_handle))
		return ui_behavior_handle

	def cast_projectile(self, proj_behavs, target):
		bitstream = BitStream()
		proj_id = self.object._v_server.new_spawned_id()
		for behav in proj_behavs:
			self.original_target_id = target.object_id
			self.serialize_behavior(behav, bitstream, target)
		delay = 1
		self.object.call_later(delay, lambda: self.request_server_projectile_impact(proj_id, target.object_id, bitstream))
		return proj_id

	@broadcast
	def echo_start_skill(self, used_mouse:bool=False, caster_latency:float=0, cast_type:c_int=0, last_clicked_posit:Vector3=(0, 0, 0), optional_originator_id:c_int64=None, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:BitStream=None, skill_id:c_uint=None, ui_skill_handle:c_uint=0):
		pass

	def start_skill(self, used_mouse:bool=False, consumable_item_id:c_int64=0, caster_latency:float=0, cast_type:c_int=0, last_clicked_posit:Vector3=Vector3.zero, optional_originator_id:c_int64=None, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:BitStream=None, skill_id:c_uint=None, ui_skill_handle:c_uint=0):
		assert not used_mouse
		assert caster_latency == 0
		assert last_clicked_posit == Vector3.zero
		assert optional_originator_id in (0, self.object.object_id)
		assert originator_rot == Quaternion(0, 0, 0, 0)

		if cast_type == CastType.Two: # casts?
			player = None # send to all including self
		else:
			player = self.object # exclude self

		self.echo_start_skill(used_mouse, caster_latency, cast_type, last_clicked_posit, optional_originator_id, optional_target_id, originator_rot, bitstream, skill_id, ui_skill_handle, player=player)

		if hasattr(self.object, "char"):
			self.object.char.update_mission_task(TaskType.UseSkill, None, skill_id)

		if optional_target_id != 0:
			if optional_target_id not in self.object._v_server.game_objects:
				return
			target = self.object._v_server.game_objects[optional_target_id]#self.object
		else:
			target = self.object
		self.picked_target_id = optional_target_id
		behavior, imagination_cost = self.object._v_server.db.skill_behavior[skill_id]
		self.object.stats.imagination -= imagination_cost
		self.original_target_id = target.object_id
		self.deserialize_behavior(behavior, bitstream, target)

		if not bitstream.all_read():
			log.warning("not all read, remaining: %s", bitstream[bitstream._read_offset//8:])

		# remove consumable
		if not self.everlasting and consumable_item_id != 0 and cast_type == CastType.Consumable:
			for item in self.object.inventory.items:
				if item is not None and item.object_id == consumable_item_id:
					self.object.inventory.remove_item_from_inv(InventoryType.Items, item)
					break

	def select_skill(self, from_skill_set:bool=False, skill_id:c_int=None):
		pass

	@broadcast
	def add_skill(self, ai_combat_weight:c_int=0, from_skill_set:bool=False, cast_type:c_int=0, time_secs:float=-1, times_can_cast:c_int=-1, skill_id:c_uint=None, slot_id:c_int=-1, temporary:bool=True):
		pass

	@single
	def remove_skill(self, from_skill_set:bool=False, skill_id:c_uint=None):
		pass

	@broadcast
	def echo_sync_skill(self, done:bool=False, bitstream:BitStream=None, ui_behavior_handle:c_uint=None, ui_skill_handle:c_uint=None):
		pass

	def sync_skill(self, done:bool=False, bitstream:BitStream=None, ui_behavior_handle:c_uint=None, ui_skill_handle:c_uint=None):
		if hasattr(self.object, "char"):
			player = self.object
		else:
			player = None
		self.echo_sync_skill(done, bitstream, ui_behavior_handle, ui_skill_handle, player=player) # don't send echo to self
		if ui_behavior_handle not in self.delayed_behaviors:
			log.error("Handle %i not handled!", ui_behavior_handle)
			return
		behavior = self.delayed_behaviors[ui_behavior_handle]
		target = self.object
		if behavior is None:
			behavior_id = bitstream.read(c_uint)
			target_id = bitstream.read(c_uint64)
			if behavior_id != 0:
				behavior = self.object._v_server.db.behavior[behavior_id]
			if target_id != 0:
				target = self.object._v_server.game_objects[target_id]

		if behavior is not None: # no, this is not an "else" from above
			self.original_target_id = target.object_id
			self.deserialize_behavior(behavior, bitstream, target)
		if not bitstream.all_read():
			log.warning("not all read, remaining: %s", bitstream[bitstream._read_offset//8:])
		if done:
			del self.delayed_behaviors[ui_behavior_handle]

	def request_server_projectile_impact(self, local_id:c_int64=0, target_id:c_int64=0, bitstream:BitStream=None):
		if target_id == 0:
			target = self.object
		else:
			if target_id not in self.object._v_server.game_objects:
				log.debug("Projectile Target %i not in game objects", target_id)
				return
			target = self.object._v_server.game_objects[target_id]

		for behav in self.projectile_behaviors[local_id]:
			self.original_target_id = target.object_id
			self.deserialize_behavior(behav, bitstream, target)
		del self.projectile_behaviors[local_id]
		# todo: do client projectile impact

	def serialize_behavior(self, behavior, bitstream, target, level=0):
		log.debug("  "*level+BehaviorTemplate(behavior.template).name+" %i", behavior.id)
		if behavior.template in TEMPLATES:
			return TEMPLATES[behavior.template].serialize(self, behavior, bitstream, target, level)

	def deserialize_behavior(self, behavior, bitstream, target, level=0):
		if behavior is None:
			return
		log.debug("  "*level+BehaviorTemplate(behavior.template).name+" %i", behavior.id)
		if behavior.template not in (BehaviorTemplate.BasicAttack, BehaviorTemplate.TacArc, BehaviorTemplate.And, BehaviorTemplate.Heal, BehaviorTemplate.MovementSwitch, BehaviorTemplate.AreaOfEffect, BehaviorTemplate.PlayEffect, BehaviorTemplate.Imagination, BehaviorTemplate.TargetCaster, BehaviorTemplate.Stun, BehaviorTemplate.Duration, BehaviorTemplate.Knockback, BehaviorTemplate.AttackDelay, BehaviorTemplate.RepairArmor, BehaviorTemplate.Switch, BehaviorTemplate.Chain, BehaviorTemplate.ChangeOrientation, BehaviorTemplate.ForceMovement, BehaviorTemplate.AlterCooldown, BehaviorTemplate.ChargeUp, BehaviorTemplate.SwitchMultiple, BehaviorTemplate.Start, BehaviorTemplate.AlterChainDelay, BehaviorTemplate.NPCCombatSkill, BehaviorTemplate.AirMovement):
			log.debug(pprint.pformat(vars(behavior), indent=level))

		if behavior.template in TEMPLATES:
			return TEMPLATES[behavior.template].deserialize(self, behavior, bitstream, target, level)

	def undo_behavior(self, behavior, params=None):
		if behavior.template == BehaviorTemplate.SpawnObject:
			self.object._v_server.destruct(params)
		elif behavior.template == BehaviorTemplate.Buff:
			if hasattr(behavior, "life"):
				self.object.stats.max_life -= behavior.life
			if hasattr(behavior, "armor"):
				self.object.stats.max_armor -= behavior.armor
			if hasattr(behavior, "imagination"):
				self.object.stats.max_imagination -= behavior.imagination
		elif behavior.template == BehaviorTemplate.Jetpack:
			self.object.char.set_jet_pack_mode(enable=False)

	def add_skill_for_item(self, item, add_buffs=True):
		if item.lot in self.object._v_server.db.object_skills:
			for skill_id in self.object._v_server.db.object_skills[item.lot]:
				behavior = self.object._v_server.db.skill_behavior[skill_id][0]
				if behavior.template in PASSIVE_BEHAVIORS:
					if add_buffs:
						if hasattr(self.object, "char"):
							self.object.char.update_mission_task(TaskType.UseSkill, None, skill_id)

						self.deserialize_behavior(behavior, b"", self.object)
				else:
					slot_id = SkillSlot.RightHand
					if item.item_type == ItemType.Hat:
						slot_id = SkillSlot.Hat
					elif item.item_type == ItemType.LeftHand:
						slot_id = SkillSlot.LeftHand
					elif item.item_type == ItemType.Neck:
						slot_id = SkillSlot.Neck
					self.add_skill(skill_id=skill_id, slot_id=slot_id)

	def add_skill_server(self, skill_id):
		behavior = self.object._v_server.db.skill_behavior[skill_id]
		if behavior.template in PASSIVE_BEHAVIORS:
			if hasattr(self.object, "char"):
				self.object.char.update_mission_task(TaskType.UseSkill, None, skill_id)

			self.deserialize_behavior(behavior, b"", self.object)

	def remove_skill_for_item(self, item):
		if item.lot in self.object._v_server.db.object_skills:
			for skill_id in self.object._v_server.db.object_skills[item.lot]:
				behavior = self.object._v_server.db.skill_behavior[skill_id][0]
				if behavior.template in PASSIVE_BEHAVIORS:
					self.undo_behavior(behavior)
				else:
					self.remove_skill(skill_id=skill_id)

	def remove_skill_server(self, skill_id):
		behavior = self.object._v_server.db.skill_behavior[skill_id][0]
		if behavior.template in PASSIVE_BEHAVIORS:
			self.undo_behavior(behavior)
