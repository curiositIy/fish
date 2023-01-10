from re import Pattern, compile as comp, VERBOSE

IMAGE_URL_RE = comp(r"^(https?://)(\S)*((?P<filename>png|jpe?g|gif|webp)$)")
BOT_MENTION_RE = comp(r"<@!?876391494485950504>")
DISCORD_ID_RE = comp(r"([0-9]{15,20})$")
OSU_BEATMAPSET_RE: Pattern = comp(
    r"https://osu.ppy.sh/beatmapsets/(?P<set>[0-9]{1,})#(?P<mode>osu|taiko|fruits|mania)/(?P<map>[0-9]{1,})"
)
OSU_BEATMAP_RE: Pattern = comp(r"https://osu.ppy.sh/beatmaps/(?P<id>[0-9]{1,})")
OSU_ID_RE: Pattern = comp(r"(?P<id>[0-9]{1,})")
TENOR_PAGE_RE: Pattern = comp(r"https?://(www\.)?tenor\.com/view/\S+")
TENOR_GIF_RE: Pattern = comp(r"https?://(www\.)?c\.tenor\.com/\S+/\S+\.gif")
CUSTOM_EMOJI_RE: Pattern = comp(r"<(a)?:([a-zA-Z0-9_]{2,32}):([0-9]{18,22})>")
TIKTOK_RE: Pattern = comp(
    r"https://(www|vt|vm|m).tiktok.com/(@)?[a-zA-Z0-9_-]{3,}(/video/[0-9]{1,})?"
)
INSTAGRAM_RE: Pattern = comp(
    r"https://(www.)?instagram.com/(p|tv|reel)/[a-zA-Z0-9-_]{5,}"
)
TWITCH_RE: Pattern = comp(r"https?://clips.twitch.tv/[a-zA-Z0-9_-]")
TWITTER_RE: Pattern = comp(r"https?://twitter.com/[a-zA-Z0-9_]{1,}/status/[0-9]{19}")
REDDIT_RE: Pattern = comp(
    r"https?://(www.)reddit.com/r/[a-zA-Z0-9_-]{1,20}/comments/[a-z0-9]{6}"
)
YT_CLIP_RE: Pattern = comp(r"https://(www.)?youtube.com/clip/[A-Za-z0-9_-]{1,}")
YT_SHORT_RE: Pattern = comp(r"https://(www.)?youtube.com/shorts/[a-zA-Z0-9_-]{11}")
YOUTUBE_RE: Pattern = comp(
    r"https://(www.)?youtu(.be|be.com)/(watch\?v=[a-zA-Z0-9_-]{11}|[a-zA-Z0-9_-]{11})"
)
VIDEOS_RE = comp(
    r"""
    (?P<tiktok>(https://(www|vt|vm|m).tiktok.com/(@)?[a-zA-Z0-9_-]{3,}(/video/[0-9]{1,})?))?
    (?P<instagram>(https://(www.)?instagram.com/(p|tv|reel)/[a-zA-Z0-9-_]{5,}))?
    (?P<twitch>(https?://clips.twitch.tv/[a-zA-Z0-9_-]*))?
    (?P<twitter>(https?://twitter.com/[a-zA-Z0-9_]{1,}/status/[0-9]{19}))?
    (?P<reddit>(https?://(www.)?reddit.com/r/[a-zA-Z0-9_-]{1,20}/comments/[a-z0-9]{6}))?
    (?P<youtube_clip>(https://youtube.com/clip/[A-Za-z0-9_-]{1,}))?
    (?P<youtube>(https://(www.)?youtu(.be|be.com)/(watch\?v=[a-zA-Z0-9_-]{11}|[a-zA-Z0-9_-]{11})))?
    (?P<youtube_shorts>(https://(www.)?youtube.com/shorts/[a-zA-Z0-9_-]{11}))?
    """,
    VERBOSE,
)
