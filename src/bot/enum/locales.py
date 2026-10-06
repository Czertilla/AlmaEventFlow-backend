from enum import Enum

from core.utils.enum.prefix import prefix


class Locale(Enum):
    en = "en"
    ru = "ru"


class LocaleKey(Enum):
	title = "title"
	"""%{ch} English"""
	description = "description"
	"""AlmaEventFlow bot for student collectives: event notifications, one-tap
	attendance marks and announcements in your collective's group chat.
	Send /start to connect your account and open the menu."""
	short_description = "short_description"
	"""Event notifications, attendance marks and announcements for AlmaEventFlow."""
	@prefix("help.")
	class Help(Enum):
		title = "title"
		"""<b>Help</b>"""
		private = "private"
		"""/start — main menu
		/help — this message
		/language — interface language"""
		unlinked = "unlinked"
		"""/link — how to connect your AlmaEventFlow account"""
		linked = "linked"
		"""/account — your account and notifications"""
		leader = "leader"
		"""/collectives — your collectives and their group chats"""
		superuser = "superuser"
		"""/admin — admin panel"""
		group = "group"
		"""<b>In a group chat</b> (for chat administrators who lead a collective)
		/setup_chat — make this chat the official chat of your collective
		/setup_chat status — which collective this chat belongs to
		/setup_chat off — disconnect this chat"""
	@prefix("menu.")
	class Menu(Enum):
		info = "info"
		"""<b>About</b>
		This is the AlmaEventFlow bot. It sends you notifications about events,
		lets you mark "going / not going" in one tap, and posts announcements to
		the official group chat of a collective.
		<blockquote expandable>A group chat can be the official chat of exactly one collective, and a collective has exactly one official chat. Only a collective leader who is also an administrator of the chat can connect it.</blockquote>"""
		@prefix("main.")
		class Main(Enum):
			title = "title"
			"""<b>Main menu</b>"""
			welcome = "welcome"
			"""<b>Welcome to AlmaEventFlow!</b>
			I send event notifications, let you mark attendance in one tap and post announcements to collectives' group chats.
			
			<blockquote>To get started, connect your Telegram to your AlmaEventFlow account.</blockquote>"""
			@prefix("items.")
			class Items(Enum):
				account = "account"
				"""%{ch} My account"""
				lang = "lang"
				"""%{ch} Language"""
				info = "info"
				"""%{ch} About"""
				link = "link"
				"""%{ch} Connect account"""
				site = "site"
				"""%{ch} Website"""
				collectives = "collectives"
				"""%{ch} My collectives"""
		@prefix("language.")
		class Language(Enum):
			title = "title"
			"""<b>Choose a language</b>
			<blockquote>Current: %{current_lang}</blockquote>"""
			@prefix("items.")
			class Items(Enum):
				sys = "sys"
				"""%{ch} System"""
		@prefix("link.")
		class Link(Enum):
			steps = "steps"
			"""<b>Connect your account</b>
			1. Sign in on the website, or register.
			2. Open "Profile" and press "Connect Telegram".
			3. Follow the link it gives you — it opens this chat and you are done.
			<blockquote expandable>The connection tells me which collectives you belong to, so that I can notify you about their events and let you mark attendance. You can disconnect at any time in /account.</blockquote>"""
	@prefix("account.")
	class Account(Enum):
		title = "title"
		"""<b>Account</b>"""
		connected = "connected"
		"""✅ Your Telegram is connected to an AlmaEventFlow account."""
		notifications_state_on = "notifications_state_on"
		"""🔔 Telegram notifications are on"""
		notifications_state_off = "notifications_state_off"
		"""🔕 Telegram notifications are off"""
		roles_none = "roles_none"
		"""You are not in any collective yet."""
		roles_member = "roles_member"
		"""👥 Member of: %{collectives}"""
		roles_leader = "roles_leader"
		"""🎓 You lead: %{collectives}"""
		roles_unknown = "roles_unknown"
		"""Couldn't load your collectives right now."""
		linked = "linked"
		"""%{ch} Your Telegram is linked to an AlmaEventFlow account."""
		not_linked = "not_linked"
		"""%{ch} Your Telegram isn't connected to an AlmaEventFlow account yet.
		Without it I can't tell which collectives you belong to."""
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
	@prefix("leader.")
	class Leader(Enum):
		list = "list"
		"""<b>My collectives</b>
		Pick one to manage its official chat and announcement settings."""
		list_empty = "list_empty"
		"""You don't lead any collective yet."""
		not_leader = "not_leader"
		"""%{ch} This section is for collective leaders."""
		stale = "stale"
		"""%{ch} You no longer lead that collective."""
		load_error = "load_error"
		"""%{ch} Couldn't load your collectives. Try again later."""
		card_title = "card_title"
		"""<b>%{name}</b>"""
		chat_none = "chat_none"
		"""💬 No chat connected"""
		chat_bound = "chat_bound"
		"""💬 Chat: %{title}"""
		chat_topic = "chat_topic"
		"""%{base} (topic)"""
		chat_unavailable = "chat_unavailable"
		"""💬 Chat is unavailable — the bot may have been removed from it"""
		chat_bot_not_admin = "chat_bot_not_admin"
		"""⚠️ The bot is not an admin there, announcements may not go through"""
		settings = "settings"
		"""🔔 Announcements: %{announce}
		🔕 Silent: %{silent}
		📌 Pin: %{pin}
		🌐 Language: %{language}"""
		@prefix("state.")
		class State(Enum):
			on = "on"
			"""on"""
			off = "off"
			"""off"""
		@prefix("lang.")
		class Lang(Enum):
			ru = "ru"
			"""Русский"""
			en = "en"
			"""English"""
		bind_hint = "bind_hint"
		"""<blockquote>Press "Connect a group" and pick a group — the bot joins with the right permissions. Or add the bot yourself, make it an admin and send /setup_chat there.</blockquote>"""
		unbound = "unbound"
		"""🔌 Chat disconnected."""
		nothing_to_unbind = "nothing_to_unbind"
		"""There is no chat to disconnect."""
		saved = "saved"
		"""Saved"""
	@prefix("setup_chat.")
	class SetupChat(Enum):
		not_linked = "not_linked"
		"""%{ch} First connect your Telegram to your AlmaEventFlow account — it takes a minute."""
		no_collective = "no_collective"
		"""%{ch} You don't lead any collective, so you can't connect this chat."""
		not_chat_admin = "not_chat_admin"
		"""%{ch} Only administrators of this chat can connect it."""
		not_admin = "not_admin"
		"""%{ch} Make the bot an admin in this chat first, then run this
		command again."""
		anonymous = "anonymous"
		"""%{ch} You are posting as an anonymous admin, so I can't tell who you are.
		Turn off anonymity for the moment and repeat the command."""
		ambiguous = "ambiguous"
		"""%{ch} You lead more than one collective. Pick one below:"""
		error = "error"
		"""%{ch} Couldn't check your collectives. Try again later."""
		invalid_id = "invalid_id"
		"""%{ch} Invalid collective_id."""
		already_bound = "already_bound"
		"""%{ch} This chat is already the official chat of another collective. A chat can belong to only one collective."""
		already_bound_mine = "already_bound_mine"
		"""%{ch} This chat is the official chat of «%{current}». Replace it with «%{target}»?"""
		success = "success"
		"""%{ch} <b>Done!</b> This chat is now the official chat of «%{collective}».
		Event announcements will appear here."""
		success_topic = "success_topic"
		"""%{ch} <b>Done!</b> This topic is now the place for announcements of «%{collective}»."""
		unchanged = "unchanged"
		"""%{ch} Already set up: this chat is the official chat of «%{collective}»."""
		moved = "moved"
		"""%{ch} Announcements of «%{collective}» now go here. The previous chat was disconnected."""
		old_chat = "old_chat"
		"""%{ch} This chat is no longer the official chat of «%{collective}»."""
		disabled = "disabled"
		"""%{ch} This chat is no longer bound to any collective."""
		not_bound = "not_bound"
		"""%{ch} This chat wasn't bound to a collective you lead."""
		status_bound = "status_bound"
		"""ℹ️ This chat is the official chat of «%{collective}»."""
		status_bound_other = "status_bound_other"
		"""ℹ️ This chat is the official chat of a collective."""
		status_free = "status_free"
		"""ℹ️ No collective is connected to this chat. A collective leader can send /setup_chat."""
		groups_only = "groups_only"
		"""%{ch} This command works in group chats. Add me to your collective's group and send it there."""
		cancelled = "cancelled"
		"""Cancelled"""
		open_settings = "open_settings"
		"""%{ch} Settings"""
	@prefix("group.")
	class Group(Enum):
		bot_added = "bot_added"
		"""<b>Hi! I'm the AlmaEventFlow bot.</b>
		I post event announcements for a collective and collect "going / not going" marks.
		
		To connect this chat:
		1. Make me an administrator.
		2. The collective leader sends /setup_chat."""
		bot_promoted = "bot_promoted"
		"""Thanks! Now the collective leader can send /setup_chat."""
		bot_demoted = "bot_demoted"
		"""⚠️ I'm no longer an administrator here, so announcements can't be posted."""
		released = "released"
		"""%{ch} I was removed from the chat, so it was disconnected from «%{collective}». Announcements won't be published until you connect a chat again."""
	@prefix("attendance.")
	class Attendance(Enum):
		need_link = "need_link"
		"""Connect your Telegram to AlmaEventFlow first."""
		not_participant = "not_participant"
		"""You are not a participant of this event."""
		yes = "yes"
		"""Marked: going ✅"""
		no = "no"
		"""Marked: not going ❌"""
		unavailable = "unavailable"
		"""Couldn't load your data. Try again later."""
		save_error = "save_error"
		"""Couldn't save your mark. Try again later."""
		button_yes = "button_yes"
		"""✅ Going"""
		button_no = "button_no"
		"""❌ Not going"""
	@prefix("fallback.")
	class Fallback(Enum):
		private = "private"
		"""%{ch} I didn't get that. Pick an action in the menu or send /help."""
	@prefix("announcement.")
	class Announcement(Enum):
		title = "title"
		"""📢 <b>%{event_name}</b>"""
		title_linked = "title_linked"
		"""📢 <b><a href="%{action_url}">%{event_name}</a></b>"""
		date = "date"
		"""🗓 %{date}"""
		location = "location"
		"""📍 %{location}"""
		organizer = "organizer"
		"""🏢 %{organizer}"""
		stages_header = "stages_header"
		"""<b>Schedule:</b>"""
		stage_line = "stage_line"
		"""▫️ <b>%{name}</b> %{time}"""
		stage_description = "stage_description"
		"""   <i>%{description}</i>"""
		stages_more = "stages_more"
		"""▫️ …and %{rest} more"""
		cta = "cta"
		"""Mark your attendance below 👇"""
		description = "description"
		"""<blockquote>%{description}</blockquote>"""
		description_long = "description_long"
		"""<blockquote expandable>%{description}</blockquote>"""
		updated = "updated"
		"""🔄 Updated"""
	@prefix("error.")
	class Error(Enum):
		username = "username"
		"""%{ch} For the bot to work best, set a @username in your Telegram settings."""
		user_not_found = "user_not_found"
		"""User not found."""
		wip = "wip"
		"""%{ch} Work in progress."""
		unexpected = "unexpected"
		"""%{ch} Something went wrong. If it keeps happening, tell us this code:"""
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
		login = "login"
		"""%{ch} Sign in"""
		register = "register"
		"""%{ch} Register"""
		profile = "profile"
		"""%{ch} Profile"""
		announce = "announce"
		"""🔔 Announcements: %{state}"""
		silent = "silent"
		"""🔕 Silent: %{state}"""
		pin = "pin"
		"""📌 Pin: %{state}"""
		language = "language"
		"""🌐 Language: %{state}"""
		bind_group = "bind_group"
		"""➕ Connect a group"""
		unbind = "unbind"
		"""🔌 Disconnect chat"""
		replace = "replace"
		"""♻️ Replace"""
		open_event = "open_event"
		"""🔗 Open event"""
		start_bot = "start_bot"
		"""🤖 Open the bot"""