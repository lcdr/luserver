import asyncio

from luserver.amf3 import AMF3
from luserver.interfaces.plugin import ChatCommand

class PlayAnim(ChatCommand):
	def __init__(self):
		super().__init__("playanim")
		self.command.add_argument("name")

	def run(self, args, sender):
		sender.render.play_animation(args.name)

class PlayCine(ChatCommand):
	def __init__(self):
		super().__init__("playcine")
		self.command.add_argument("name")
		self.command.add_argument("--hideui", action="store_true", default=False)
		self.command.add_argument("--showplayer", action="store_true", default=False)

	def run(self, args, sender):
		if args.hideui:
			# hide HUD
			sender.char.u_i_message_server_to_single_client(message_name=b"pushGameState", args=AMF3({"state": "front_end"}))
		sender.char.camera.play_cinematic(path_name=args.name, send_server_notify=args.hideui, hide_player_during_cine=not args.showplayer, start_time_advance=0)

class PlayEmote(ChatCommand):
	def __init__(self):
		super().__init__("playemote")
		self.command.add_argument("id", type=int)

	def run(self, args, sender):
		sender.char.emote_played(args.id, None)

class PlayFX(ChatCommand):
	def __init__(self):
		super().__init__("playfx")
		self.command.add_argument("id", type=int)
		self.command.add_argument("type")

	def run(self, args, sender):
		sender.render.play_f_x_effect(name=b"", effect_id=args.id, effect_type=args.type)

class PlaySound(ChatCommand):
	def __init__(self):
		super().__init__("playsound", aliases=("ps",))
		self.command.add_argument("id")

	def run(self, args, sender):
		sender.render.play_n_d_audio_emitter(event_guid=args.id.encode(), meta_event_name=b"")

class PlayStuff(ChatCommand):
	def __init__(self):
		super().__init__("playstuff")
		self.command.add_argument("--bpm", type=int, default=114)
		self.notes = {
			"C1": b"{6f33a653-6446-4ec9-9e0d-9552871a52bb}",
			"C#1": b"{97aa64a3-89a3-4a9f-a370-c7cb5af66937}",
			"D1": b"{3f3cfeaa-371a-44aa-89a0-68bbaa995997}",
			"D#1": b"{0ec81367-a91c-40f8-a72e-e99a05d2b612}",
			"E1": b"{7b8d02a5-986a-4526-bb93-ff229af44198}",
			"F1": b"{fdf4a54e-126f-4a22-90b1-854b9e0ac232}",
			"F#1": b"{9739af13-6b0f-4420-8306-c3709a350f0f}",
			"G1": b"{b3e2e91e-e359-4fc5-829a-45c43a188552}",
			"G#1": b"{4271bd1f-36eb-4362-acc9-669d6ab9f426}",
			"A1": b"{45b34354-2198-42f6-a6a2-0d52cb2342d4}",
			"A#1": b"{d2a79895-1037-4cb8-8692-0c1167290538}",
			"B1": b"{85797d72-27e7-4255-af14-e565ba75db95}",
			"C2": b"{b0e828d5-d324-4a8e-840e-480c356c0803}"
		}

	def run(self, args, sender):
		quarter = 60/args.bpm
		half = 2*quarter
		full = 2*half
		dotquarter = quarter * 1.5
		eighth = quarter / 2
		sixteenth = eighth / 2
		song = [
			("C#1", dotquarter),
			("D#1", dotquarter),
			("G#1", quarter),
			("D#1", dotquarter),
			("F1", dotquarter),
			("G#1", sixteenth),
			("F#1", sixteenth),
			("F1", sixteenth),
			("D#1", sixteenth),
			("C#1", dotquarter),
			("D#1", dotquarter),
			("G#1", quarter),
			("D#1", quarter),
			("C#1", quarter),
		]

		last_time = 0
		for note, dur in song:
			asyncio.get_event_loop().call_later(last_time, self.play_note, note, sender)
			last_time += dur

	def play_note(self, note, sender):
		sender.render.play_n_d_audio_emitter(event_guid=self.notes[note], meta_event_name=b"")
