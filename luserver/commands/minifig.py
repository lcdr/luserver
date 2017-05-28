from ..modules.char import EyeStyle, MouthStyle
from .command import ChatCommand

class MinifigCommand(ChatCommand):
	def __init__(self, chat, name):
		super().__init__(chat, name)
		self.command.add_argument("--permanent", action="store_true", default=False)

	def run(self, args, sender):
		eye_style = sender.char.eye_style
		eyebrow_style = sender.char.eyebrow_style
		hair_color = sender.char.hair_color
		hair_style = sender.char.hair_style
		mouth_style = sender.char.mouth_style
		self.sub_run(args, sender)
		self.chat.server.construct(sender, new=False)
		if not args.permanent:
			sender.char.eye_style = eye_style
			sender.char.eyebrow_style = eyebrow_style
			sender.char.hair_color = hair_color
			sender.char.hair_style = hair_style
			sender.char.mouth_style = mouth_style

	def sub_run(self, args, sender):
		raise NotImplementedError

class EyebrowsCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "eyebrows")
		self.command.add_argument("value", type=int)

	def sub_run(self, args, sender):
		sender.char.eyebrow_style = args.value

class EyesCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "eyes")
		self.command.add_argument("value", type=int)

	def sub_run(self, args, sender):
		sender.char.eye_style = args.value

class HairColorCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "haircolor")
		self.command.add_argument("value", type=int)

	def sub_run(self, args, sender):
		sender.char.hair_color = args.value

class HairStyleCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "hairstyle")
		self.command.add_argument("value", type=int)

	def sub_run(self, args, sender):
		if args.value > 10:
			self.chat.sys_msg_sender("invalid style")
			return
		sender.char.hair_style = args.value

class MouthCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "mouth")
		self.command.add_argument("value", type=int)

	def sub_run(self, args, sender):
		sender.char.mouth_style = args.value

class StyleCommand(MinifigCommand):
	styles = {
		"creepy": (8, EyeStyle.RedEyes, MouthStyle.LargeSmile),
		"robot": (0, EyeStyle.Robot, MouthStyle.Robot),
		"security": (4, EyeStyle.Sunglasses, MouthStyle.HeadSet)}

	def __init__(self, chat):
		super().__init__(chat, "style")
		self.command.add_argument("style", choices=tuple(self.styles))

	def sub_run(self, args, sender):
		hair_style, eye_style, mouth_style = self.styles[args.style]
		sender.char.hair_style = hair_style
		sender.char.eye_style = eye_style
		sender.char.mouth_style = mouth_style


# for internal builds only - due to name change this will cause bugs when used incorrectly!
class LCDRCommand(MinifigCommand):
	def __init__(self, chat):
		super().__init__(chat, "lcdr")

	def sub_run(self, args, sender):
		sender.name = "lcdr"
		sender.char.hair_color = 10
		sender.char.hair_style = 7
		sender.char.eyebrow_style = 22
		sender.char.eye_style = 1
		sender.char.mouth_style = 24
