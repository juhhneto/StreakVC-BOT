"""
i18n.py — All user-facing strings for the bot in PT-BR and EN.
Access via:  from i18n import t, set_lang, get_lang
"""

_STRINGS = {
    "pt": {
        # General
        "server_only":          "Use este comando em um servidor.",
        "db_error":             "Ocorreu um erro ao buscar seus dados. Tente novamente.",
        "ranking_error":        "Erro ao buscar o ranking. Tente novamente.",

        # /join
        "join_not_in_vc":       "❌ Você precisa estar em um canal de voz para usar este comando!",
        "join_already":         "Já estou em **{channel}**!",
        "join_success":         "✅ Conectado ao canal **{channel}**! Monitorando o tempo de voz. 🎙️",

        # /leave
        "leave_not_connected":  "Não estou em nenhum canal de voz.",
        "leave_msg":            "👋 Saí do canal **{channel}** e salvei as sessões abertas.",
        "leave_saved":          "\n> Sessões salvas: {names}",

        # /streak embed
        "streak_title":         "📅 Frequência de {name}",
        "streak_field_streak":  "🔥 Frequência Atual",
        "streak_field_time":    "⏰ Tempo em Voz Hoje",
        "streak_field_level":   "{emoji} Nível {level} — {title}",
        "streak_none":          "{icon} **Sem frequência :/**",
        "streak_day":           "{icon} **{n}** dia",
        "streak_days":          "{icon} **{n}** dias",
        "streak_footer_need":   "Faltam {min} min hoje para registrar sua frequência! ⏳",
        "streak_footer_done":   "Frequência de hoje garantida! Continue assim para manter sua chama viva! 🔥",
        "streak_max_xp":        "**Nível máximo atingido!** 👑",

        # /ranking embed
        "ranking_title":        "🏆 Ranking Semanal de Voz",
        "ranking_desc":         "Os usuários com mais tempo em chat de voz essa semana!",
        "ranking_empty":        "Nenhuma atividade registrada ainda esta semana. Seja o primeiro!",
        "ranking_week_time":    "⏰ **{time}** esta semana",
        "ranking_streak":       "{icon} **{n}** {label} de frequência consecutiva",
        "ranking_day":          "dia",
        "ranking_days":         "dias",
        "ranking_footer":       "O ranking reseta toda segunda-feira. 📅",

        # /language
        "lang_changed":         "✅ Idioma alterado para **Português**! 🇧🇷",
        "lang_already":         "O idioma já está definido como **Português**.",
        "lang_cmd_desc":        "Muda o idioma do bot (Português / English).",
        "lang_choice_pt":       "Português 🇧🇷",
        "lang_choice_en":       "English 🇺🇸",

        # Level titles
        "level_1": "Novato",
        "level_2": "Aprendiz",
        "level_3": "Membro",
        "level_4": "Veterano",
        "level_5": "Elite",
        "level_6": "Lendário",

        # Command descriptions (used in tree.command)
        "cmd_join_desc":   "Faz o bot entrar no seu canal de voz atual.",
        "cmd_leave_desc":  "Faz o bot sair do canal de voz e salva as sessões abertas.",
        "cmd_streak_desc": "Mostra sua frequência atual, tempo de voz hoje e nível do dia.",
        "cmd_rank_desc":   "Mostra o top 3 com maior tempo de voz na semana.",
    },

    "en": {
        # General
        "server_only":          "This command can only be used in a server.",
        "db_error":             "An error occurred while fetching your data. Please try again.",
        "ranking_error":        "Error fetching the ranking. Please try again.",

        # /join
        "join_not_in_vc":       "❌ You need to be in a voice channel to use this command!",
        "join_already":         "I'm already in **{channel}**!",
        "join_success":         "✅ Connected to **{channel}**! Now monitoring voice time. 🎙️",

        # /leave
        "leave_not_connected":  "I'm not in any voice channel.",
        "leave_msg":            "👋 Left **{channel}** and saved all open sessions.",
        "leave_saved":          "\n> Sessions saved: {names}",

        # /streak embed
        "streak_title":         "📅 Streak of {name}",
        "streak_field_streak":  "🔥 Current Streak",
        "streak_field_time":    "⏰ Voice Time Today",
        "streak_field_level":   "{emoji} Level {level} — {title}",
        "streak_none":          "{icon} **No streak :/**",
        "streak_day":           "{icon} **{n}** day",
        "streak_days":          "{icon} **{n}** days",
        "streak_footer_need":   "{min} more min in VC today to lock in your streak! ⏳",
        "streak_footer_done":   "Today's streak is secured! Keep it up! 🔥",
        "streak_max_xp":        "**Max level reached!** 👑",

        # /ranking embed
        "ranking_title":        "🏆 Weekly Voice Ranking",
        "ranking_desc":         "Users with the most voice channel time this week!",
        "ranking_empty":        "No activity recorded yet this week. Be the first!",
        "ranking_week_time":    "⏰ **{time}** this week",
        "ranking_streak":       "{icon} **{n}** {label} streak",
        "ranking_day":          "day",
        "ranking_days":         "days",
        "ranking_footer":       "Ranking resets every Monday. 📅",

        # /language
        "lang_changed":         "✅ Language changed to **English**! 🇺🇸",
        "lang_already":         "The language is already set to **English**.",
        "lang_cmd_desc":        "Change the bot language (Português / English).",
        "lang_choice_pt":       "Português 🇧🇷",
        "lang_choice_en":       "English 🇺🇸",

        # Level titles
        "level_1": "Rookie",
        "level_2": "Apprentice",
        "level_3": "Member",
        "level_4": "Veteran",
        "level_5": "Elite",
        "level_6": "Legendary",

        # Command descriptions
        "cmd_join_desc":   "Make the bot join your current voice channel.",
        "cmd_leave_desc":  "Make the bot leave the voice channel and save open sessions.",
        "cmd_streak_desc": "Show your current streak, today's voice time and daily level.",
        "cmd_rank_desc":   "Show the top 3 users with the most voice time this week.",
    },
}

# Default language
_current_lang: str = "pt"

def set_lang(lang: str):
    global _current_lang
    if lang in _STRINGS:
        _current_lang = lang

def get_lang() -> str:
    return _current_lang

def t(key: str, **kwargs) -> str:
    """Translate a key to the current language, formatting any kwargs."""
    text = _STRINGS.get(_current_lang, _STRINGS["pt"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text