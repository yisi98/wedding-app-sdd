"""Minimal trilingual (en/zh/ru) message catalog for API-generated strings.

Every user-facing API message MUST have an entry in all three languages (constitution
quality bar: EN/ZH/RU parity). `t(key, lang)` resolves a message, falling back to English
for an unknown language and to the key itself for an unknown message.
"""

MESSAGES: dict[str, dict[str, str]] = {
    "invalid_event_password": {
        "en": "Incorrect event password.",
        "zh": "活动密码不正确。",
        "ru": "Неверный пароль мероприятия.",
    },
    "invalid_refresh_token": {
        "en": "Invalid or expired session. Please sign in again.",
        "zh": "会话无效或已过期，请重新登录。",
        "ru": "Сессия недействительна или истекла. Войдите снова.",
    },
    "not_authenticated": {
        "en": "Authentication required.",
        "zh": "需要登录。",
        "ru": "Требуется аутентификация.",
    },
    "account_inactive": {
        "en": "This account has been deactivated.",
        "zh": "此账户已被停用。",
        "ru": "Эта учётная запись отключена.",
    },
    "admin_required": {
        "en": "Administrator access required.",
        "zh": "需要管理员权限。",
        "ru": "Требуются права администратора.",
    },
}

DEFAULT_LANG = "en"
SUPPORTED = ("en", "zh", "ru")


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    lang = lang if lang in SUPPORTED else DEFAULT_LANG
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry[DEFAULT_LANG])
