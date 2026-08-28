from enum import Enum

from core.utils.enum.prefix import prefix


class Locale(Enum):
    en = "en"
    ru = "ru"


class LocaleKey(Enum):
	title = "title"
	"""%{ch} English"""
	description = "description"
	"""AlmaEventFlow bot — link your Telegram to your AEF account and get
	event notifications. Use /start to open the menu."""
	help = "help"
	"""<b>Help</b>
	
	/start — open the main menu
	/account — manage your linked AlmaEventFlow account
	/language — change the interface language
	/help — show this message
	/setup_chat — set this group chat as a collective's official chat
	(groups only, for collective principals)"""
	@prefix("start.")
	class Start(Enum):
		greeting = "greeting"
		"""<b>Welcome to AlmaEventFlow!</b>
		Pick an action below."""
	@prefix("menu.")
	class Menu(Enum):
		info = "info"
		"""<b>About</b>
		This is the AlmaEventFlow bot. Link your Telegram to your AEF account
		to receive event notifications here."""
		@prefix("main.")
		class Main(Enum):
			title = "title"
			"""<b>Main menu</b>"""
			@prefix("items.")
			class Items(Enum):
				account = "account"
				"""%{ch} My account"""
				lang = "lang"
				"""%{ch} Language"""
				info = "info"
				"""%{ch} About"""
		@prefix("language.")
		class Language(Enum):
			title = "title"
			"""<b>Choose a language</b>
			<blockquote>Current: %{current_lang}</blockquote>"""
			@prefix("items.")
			class Items(Enum):
				sys = "sys"
				"""%{ch} System"""
	@prefix("account.")
	class Account(Enum):
		linked = "linked"
		"""%{ch} Your Telegram is linked to an AlmaEventFlow account."""
		not_linked = "not_linked"
		"""%{ch} Your Telegram isn't linked yet.
		Open your profile on the AlmaEventFlow website and connect Telegram
		there — it will send you a link to open here."""
		confirm_unlink = "confirm_unlink"
		"""%{ch} Unlink Telegram from your AlmaEventFlow account?"""
		unlinked = "unlinked"
		"""%{ch} Telegram unlinked."""
		linked_success = "linked_success"
		"""%{ch} Telegram linked to your AlmaEventFlow account!"""
		link_invalid = "link_invalid"
		"""%{ch} This link is invalid. Request a new one on the website."""
		link_expired = "link_expired"
		"""%{ch} This link has expired. Request a new one on the website."""
		notifications_on = "notifications_on"
		"""%{ch} Telegram notifications turned on."""
		notifications_off = "notifications_off"
		"""%{ch} Telegram notifications turned off."""
		notifications_error = "notifications_error"
		"""%{ch} Couldn't change that setting. Try again later."""
	@prefix("setup_chat.")
	class SetupChat(Enum):
		not_linked = "not_linked"
		"""%{ch} First link your Telegram to your AlmaEventFlow account in a
		private message with the bot: /account"""
		not_admin = "not_admin"
		"""%{ch} Make the bot an admin in this chat first, then run this
		command again."""
		no_collective = "no_collective"
		"""%{ch} You don't lead any collective."""
		ambiguous = "ambiguous"
		"""%{ch} You lead more than one collective. Pick one below:"""
		error = "error"
		"""%{ch} Couldn't check your collectives. Try again later."""
		invalid_id = "invalid_id"
		"""%{ch} Invalid collective_id."""
		success = "success"
		"""%{ch} Done! This chat is now the official chat for that collective."""
		disabled = "disabled"
		"""%{ch} This chat is no longer bound to any collective."""
		not_bound = "not_bound"
		"""%{ch} This chat wasn't bound to a collective you lead."""
	@prefix("error.")
	class Error(Enum):
		username = "username"
		"""%{ch} For the bot to work best, set a @username in your Telegram settings."""
		user_not_found = "user_not_found"
		"""User not found."""
		wip = "wip"
		"""%{ch} Work in progress."""
	@prefix("button.")
	class Button(Enum):
		back = "back"
		"""%{ch} Back"""
		cancel = "cancel"
		"""%{ch} Cancel"""
		confirm = "confirm"
		"""%{ch} Confirm"""
		add = "add"
		"""%{ch} Add"""
		delete = "delete"
		"""%{ch} Delete"""
		unlink = "unlink"
		"""%{ch} Unlink"""
		notifications = "notifications"
		"""%{ch} Telegram notifications"""