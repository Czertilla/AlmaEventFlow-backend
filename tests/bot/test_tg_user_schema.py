from bot.tg.schema.user import TGUser


def test_a_user_without_a_language_code_is_valid():
    user = TGUser(id=1, is_bot=False, first_name="A")

    assert user.language_code is None


def test_the_language_code_is_lowercased():
    user = TGUser(id=1, is_bot=False, first_name="A", language_code="RU")

    assert user.language_code == "ru"
