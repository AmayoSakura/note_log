import json
import html
from pathlib import Path
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone

# ============================================================
# Squall NOTE LOG
# generate_html.py
#
# Required:
#   note_data.json
# Optional:
#   data/daily_stats.json
#   data/article_history.json
# Output:
#   index.html
# ============================================================

NOTE_DATA_FILE = Path("note_data.json")
DAILY_STATS_FILE = Path("data/daily_stats.json")
ARTICLE_HISTORY_FILE = Path("data/article_history.json")
OUTPUT_FILE = Path("index.html")

SITE_URL = "https://amexfuri.work/"
NOTE_URL = "https://note.com/squallxxx"
PAGE_TITLE = "NOTE LOG — Squall"

# Squall palette (amexfuri.work セピアトーンに統一)
BG = "#f4efea"
PAPER = "#faf7f5"
INK = "#201812"
MUTED = "#695444"
LIGHT = "#ece4db"
PURPLE = "#73482a"
PURPLE_LIGHT = "#d9c3ac"
PINK = "#f0e6db"
RED = "#8a3a26"
LINE = "#e0d5c8"
HEAT_1 = "#e4d4bd"
HEAT_2 = "#c9a578"

# Dark mode palette (amexfuri.work .dark に準拠)
DARK_BG = "#1c1613"
DARK_PAPER = "#27201c"
DARK_INK = "#e8e0d4"
DARK_MUTED = "#a89a8a"
DARK_LIGHT = "#332a24"
DARK_PURPLE = "#c4a076"
DARK_PURPLE_LIGHT = "#5a4735"
DARK_PINK = "#332a24"
DARK_RED = "#d68a6a"
DARK_LINE = "#3d332c"
DARK_HEAT_1 = "#4a3c2e"
DARK_HEAT_2 = "#7a5f3f"


def hex_to_rgb_str(hex_color):
    """
    '#faf7f5' -> '250, 247, 245'
    rgba()内でCSS変数として使うための文字列に変換する。
    """
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"{r}, {g}, {b}"


PAPER_RGB = hex_to_rgb_str(PAPER)
DARK_PAPER_RGB = hex_to_rgb_str(DARK_PAPER)

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def load_json(path, default):
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def date_key(value):
    dt = parse_date(value)

    if dt:
        return dt.strftime("%Y-%m-%d")

    return str(value or "")[:10]


def format_date(value):
    dt = parse_date(value)

    if not dt:
        return str(value or "")[:10]

    return f"{dt.year}.{dt.month:02d}.{dt.day:02d}"


def format_month(value):
    dt = parse_date(value)

    if not dt:
        return str(value or "")[:7]

    return f"{dt.year}.{dt.month:02d}"


def note_url(note):
    key = note.get("key")

    if key:
        return f"https://note.com/s/{key}"

    return NOTE_URL


def magazine_url(magazine):
    key = magazine.get("key")
    urlname = creator.get("urlname")

    if key and urlname:
        return f"https://note.com/{urlname}/m/{key}"

    return NOTE_URL


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

note_data = load_json(NOTE_DATA_FILE, {})
daily_stats = load_json(DAILY_STATS_FILE, [])
article_history = load_json(ARTICLE_HISTORY_FILE, {})

creator = note_data.get("creator", {})
notes = note_data.get("notes", [])
magazines = note_data.get("magazines", [])

# 最新順
notes = sorted(
    notes,
    key=lambda x: parse_date(x.get("published_at")) or datetime.min,
    reverse=True
)

# タイトルと数値を正規化
for note in notes:
    note["title"] = str(note.get("title") or "").strip()
    note["likes"] = safe_int(note.get("likes"))
    note["comments"] = safe_int(note.get("comments"))

# マガジンは記事数の多い順
magazines = sorted(
    magazines,
    key=lambda x: safe_int(x.get("note_count")),
    reverse=True
)

for magazine in magazines:
    magazine["title"] = str(magazine.get("title") or "").strip()
    magazine["note_count"] = safe_int(magazine.get("note_count"))
    magazine["likes"] = safe_int(magazine.get("likes"))

daily_stats = sorted(
    daily_stats,
    key=lambda x: x.get("date", "")
)

# ------------------------------------------------------------
# Basic statistics
# ------------------------------------------------------------

article_count = len(notes)

total_likes = sum(
    safe_int(note.get("likes"))
    for note in notes
)

total_comments = sum(
    safe_int(note.get("comments"))
    for note in notes
)

followers = safe_int(creator.get("followerCount"))
following = safe_int(creator.get("followingCount"))

average_likes = (
    round(total_likes / article_count, 1)
    if article_count
    else 0
)

average_comments = (
    round(total_comments / article_count, 1)
    if article_count
    else 0
)

fetched_at = note_data.get("fetched_at")
updated_label = format_date(fetched_at)

# ------------------------------------------------------------
# Monthly activity
# ------------------------------------------------------------

monthly_posts = defaultdict(int)
monthly_likes = defaultdict(int)
monthly_comments = defaultdict(int)

for note in notes:
    month = format_month(note.get("published_at"))

    if month:
        monthly_posts[month] += 1
        monthly_likes[month] += safe_int(note.get("likes"))
        monthly_comments[month] += safe_int(note.get("comments"))

months = sorted(monthly_posts.keys())

# ------------------------------------------------------------
# Recent activity
# ------------------------------------------------------------

recent_30_days_posts = 0

if notes:
    latest_dt = parse_date(notes[0].get("published_at"))

    if latest_dt:
        cutoff = latest_dt - timedelta(days=29)

        for note in notes:
            dt = parse_date(note.get("published_at"))

            if dt and dt >= cutoff:
                recent_30_days_posts += 1

# ------------------------------------------------------------
# SVG line chart
# ------------------------------------------------------------

def make_line_chart(
    labels,
    values,
    width=900,
    height=300,
    stroke="var(--purple)",
    fill="var(--purple-light)",
    suffix=""
):
    if not values:
        return """
        <div class="empty-chart">
            データがまだありません。
        </div>
        """

    values = [safe_int(v) for v in values]

    max_value = max(values)
    min_value = min(values)

    if max_value == min_value:
        max_value += 1
        min_value = max(0, min_value - 1)

    padding_left = 48
    padding_right = 20
    padding_top = 24
    padding_bottom = 40

    chart_width = width - padding_left - padding_right
    chart_height = height - padding_top - padding_bottom

    points = []

    for i, value in enumerate(values):
        if len(values) == 1:
            x = padding_left + chart_width / 2
        else:
            x = padding_left + (
                chart_width * i / (len(values) - 1)
            )

        ratio = (value - min_value) / (max_value - min_value)

        y = (
            padding_top
            + chart_height
            - ratio * chart_height
        )

        points.append((x, y, value))

    point_string = " ".join(
        f"{x:.1f},{y:.1f}"
        for x, y, _ in points
    )

    area_points = (
        f"{padding_left},{padding_top + chart_height} "
        + point_string
        + f" {points[-1][0]:.1f},{padding_top + chart_height}"
    )

    # 横グリッド
    grid = ""

    for i in range(5):
        ratio = i / 4
        y = padding_top + chart_height * ratio

        value = max_value - (
            (max_value - min_value) * ratio
        )

        grid += f"""
        <line
            x1="{padding_left}"
            y1="{y:.1f}"
            x2="{width - padding_right}"
            y2="{y:.1f}"
            class="chart-grid"
        />
        <text
            x="{padding_left - 10}"
            y="{y + 4:.1f}"
            class="chart-axis"
            text-anchor="end"
        >{int(round(value))}{esc(suffix)}</text>
        """

    # Xラベル
    label_svg = ""

    step = max(1, len(labels) // 6)

    for i, label in enumerate(labels):
        if (
            i == 0
            or i == len(labels) - 1
            or i % step == 0
        ):
            x = points[i][0]

            label_svg += f"""
            <text
                x="{x:.1f}"
                y="{height - 12}"
                class="chart-axis"
                text-anchor="middle"
            >{esc(label)}</text>
            """

    circles = ""

    for x, y, value in points:
        circles += f"""
        <circle
            cx="{x:.1f}"
            cy="{y:.1f}"
            r="3.5"
            fill="{stroke}"
        >
            <title>{value}{esc(suffix)}</title>
        </circle>
        """

    return f"""
    <svg
        class="line-chart"
        viewBox="0 0 {width} {height}"
        preserveAspectRatio="none"
        aria-hidden="true"
    >
        <defs>
            <linearGradient
                id="chartFill"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="{fill}"
                    stop-opacity="0.42"
                />
                <stop
                    offset="100%"
                    stop-color="{fill}"
                    stop-opacity="0"
                />
            </linearGradient>
        </defs>

        {grid}

        <polygon
            points="{area_points}"
            fill="url(#chartFill)"
        />

        <polyline
            points="{point_string}"
            fill="none"
            stroke="{stroke}"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        {circles}
        {label_svg}
    </svg>
    """

# ------------------------------------------------------------
# Daily chart data
# ------------------------------------------------------------

daily_labels = [
    date_key(item.get("date"))
    for item in daily_stats
]

daily_followers = [
    safe_int(item.get("followers"))
    for item in daily_stats
]

daily_likes = [
    safe_int(item.get("total_likes"))
    for item in daily_stats
]

daily_posts = [
    safe_int(item.get("note_count"))
    for item in daily_stats
]

followers_chart = make_line_chart(
    daily_labels,
    daily_followers,
    stroke="var(--purple)",
    fill="var(--purple-light)"
)

likes_chart = make_line_chart(
    daily_labels,
    daily_likes,
    stroke="var(--red)",
    fill="var(--pink)"
)

posts_chart = make_line_chart(
    daily_labels,
    daily_posts,
    stroke="var(--muted)",
    fill="var(--light)"
)

# ------------------------------------------------------------
# Monthly activity chart
# ------------------------------------------------------------

def make_monthly_bars(months, values):
    if not months:
        return """
        <div class="empty-chart">
            データがまだありません。
        </div>
        """

    max_value = max(values) if values else 1
    max_value = max(max_value, 1)

    bars = ""

    for month, value in zip(months, values):
        height = max(4, (value / max_value) * 150)

        bars += f"""
        <div class="bar-column">
            <div class="bar-value">{value}</div>

            <div
                class="bar"
                style="height:{height:.1f}px"
                title="{esc(month)}：{value}本"
            ></div>

            <div class="bar-label">
                {esc(month[-5:])}
            </div>
        </div>
        """

    return f"""
    <div class="bar-chart">
        {bars}
    </div>
    """

monthly_chart = make_monthly_bars(
    months,
    [monthly_posts[m] for m in months]
)

# ------------------------------------------------------------
# Activity heatmap
# ------------------------------------------------------------

def make_activity_heatmap(notes):
    counts = defaultdict(int)

    for note in notes:
        key = date_key(note.get("published_at"))

        if key:
            counts[key] += 1

    if not counts:
        return """
        <div class="empty-chart">
            投稿データがまだありません。
        </div>
        """

    latest = max(counts.keys())

    try:
        latest_date = date.fromisoformat(latest)
    except ValueError:
        return ""

    # 16週間
    start = latest_date - timedelta(days=111)

    # 月曜始まり
    start -= timedelta(days=start.weekday())

    cells = []

    for i in range(16 * 7):
        current = start + timedelta(days=i)
        key = current.isoformat()
        count = counts.get(key, 0)

        if count == 0:
            level = 0
        elif count == 1:
            level = 1
        elif count == 2:
            level = 2
        else:
            level = 3

        cells.append(
            f"""
            <span
                class="heat-cell level-{level}"
                title="{current.strftime('%Y.%m.%d')}：{count}本"
            ></span>
            """
        )

    return f"""
    <div class="heatmap-wrap">
        <div class="weekday-labels">
            <span>月</span>
            <span>水</span>
            <span>金</span>
        </div>

        <div class="heatmap">
            {"".join(cells)}
        </div>
    </div>

    <div class="heat-legend">
        <span>少ない</span>
        <i class="heat-cell level-0"></i>
        <i class="heat-cell level-1"></i>
        <i class="heat-cell level-2"></i>
        <i class="heat-cell level-3"></i>
        <span>多い</span>
    </div>
    """

heatmap = make_activity_heatmap(notes)

# ------------------------------------------------------------
# Writing pace: streaks
# ------------------------------------------------------------

def compute_weekly_streaks(notes):
    """
    週（月曜始まり）単位で「1本以上投稿した週」の連続記録を数える。
    """
    dates = sorted({
        date_key(note.get("published_at"))
        for note in notes
        if note.get("published_at")
    })

    dates = [d for d in dates if d]

    if not dates:
        return {
            "longest": 0,
            "current": 0,
            "recent_weeks": [],
        }

    parsed_dates = sorted(
        date.fromisoformat(d) for d in dates
    )

    def week_start(d):
        return d - timedelta(days=d.weekday())

    posted_weeks = sorted({
        week_start(d) for d in parsed_dates
    })

    # 最長連続週数
    longest = 1
    current_run = 1

    for i in range(1, len(posted_weeks)):
        gap_weeks = (
            (posted_weeks[i] - posted_weeks[i - 1]).days // 7
        )

        if gap_weeks == 1:
            current_run += 1
        elif gap_weeks > 1:
            longest = max(longest, current_run)
            current_run = 1

    longest = max(longest, current_run)

    # 現在進行中の連続週数（今週 or 先週から遡って連続しているか）
    JST = timezone(timedelta(hours=9))
    today_local = datetime.now(JST).date()
    this_week_start = week_start(today_local)

    latest_posted_week = posted_weeks[-1]
    gap_from_this_week = (
        (this_week_start - latest_posted_week).days // 7
    )

    if gap_from_this_week > 1:
        current_streak = 0
    else:
        current_streak = 1

        for i in range(len(posted_weeks) - 1, 0, -1):
            gap_weeks = (
                (posted_weeks[i] - posted_weeks[i - 1]).days // 7
            )

            if gap_weeks == 1:
                current_streak += 1
            else:
                break

    # 直近12週間の週間投稿数
    recent_weeks = []

    for i in range(11, -1, -1):
        target_week = this_week_start - timedelta(weeks=i)
        target_week_end = target_week + timedelta(days=6)

        count = sum(
            1
            for d in parsed_dates
            if target_week <= d <= target_week_end
        )

        recent_weeks.append({
            "label": f"{target_week.month}/{target_week.day}",
            "count": count,
        })

    return {
        "longest": longest,
        "current": current_streak,
        "recent_weeks": recent_weeks,
    }


def make_weekly_bars(recent_weeks):
    if not recent_weeks:
        return """
        <div class="empty-chart">
            データがまだありません。
        </div>
        """

    max_value = max(w["count"] for w in recent_weeks)
    max_value = max(max_value, 1)

    bars = ""

    for week in recent_weeks:
        height = max(4, (week["count"] / max_value) * 120)

        bars += f"""
        <div class="bar-column">
            <div class="bar-value">{week["count"]}</div>

            <div
                class="bar"
                style="height:{height:.1f}px"
                title="週{esc(week['label'])}〜：{week['count']}本"
            ></div>

            <div class="bar-label">
                {esc(week["label"])}
            </div>
        </div>
        """

    return f"""
    <div class="bar-chart">
        {bars}
    </div>
    """

streaks = compute_weekly_streaks(notes)
longest_streak = streaks["longest"]
current_streak = streaks["current"]
weekly_pace_chart = make_weekly_bars(streaks["recent_weeks"])

# ------------------------------------------------------------
# Popular articles
# ------------------------------------------------------------

popular_notes = sorted(
    notes,
    key=lambda x: (
        safe_int(x.get("likes")),
        safe_int(x.get("comments"))
    ),
    reverse=True
)[:5]

# ------------------------------------------------------------
# Popular: momentum diagnosis
# 直近10本の平均スキ数 vs 全記事平均スキ数で「勢い」を診断する。
# 単純な人気ランキングは古い記事が有利になりがちなため、
# 「絶対値」ではなく「平均との比較」で最近の反応を見る。
# ------------------------------------------------------------

def diagnose_momentum(notes):
    if len(notes) < 10:
        return None

    recent = notes[:10]

    overall_avg = (
        sum(safe_int(n.get("likes")) for n in notes) / len(notes)
    )

    recent_avg = (
        sum(safe_int(n.get("likes")) for n in recent) / len(recent)
    )

    if overall_avg == 0:
        return None

    diff_ratio = (recent_avg - overall_avg) / overall_avg

    if diff_ratio >= 0.15:
        message = "直近10本の反応、全体平均より良好。今の書き方がハマってるみたい。"
        mood = "up"
    elif diff_ratio <= -0.15:
        message = "直近10本はやや反応控えめ。テーマや切り口を変えてみる時期かも。"
        mood = "down"
    else:
        message = "直近10本の反応は、これまでの平均と近い水準。安定した巡航中。"
        mood = "flat"

    return {
        "message": message,
        "mood": mood,
        "recent_avg": round(recent_avg, 1),
        "overall_avg": round(overall_avg, 1),
    }

momentum = diagnose_momentum(notes)

if momentum:
    momentum_html = f"""
    <div class="momentum-memo momentum-{momentum['mood']}">
        <div class="momentum-label">
            📋 Momentum Check
        </div>
        <div class="momentum-text">
            {esc(momentum['message'])}
        </div>
        <div class="momentum-sub">
            直近10本 平均♥{momentum['recent_avg']}
            ／ 全体平均 ♥{momentum['overall_avg']}
        </div>
    </div>
    """
else:
    momentum_html = ""

popular_html = ""

for index, note in enumerate(popular_notes, start=1):
    title = note.get("title", "")
    likes = safe_int(note.get("likes"))
    comments = safe_int(note.get("comments"))

    popular_html += f"""
    <a
        class="popular-item"
        href="{esc(note_url(note))}"
        target="_blank"
        rel="noopener noreferrer"
    >
        <span class="popular-rank">
            {index:02d}
        </span>

        <span class="popular-title">
            {esc(title)}
        </span>

        <span class="popular-stats">
            ♥ {likes}
            <small>／ 💬 {comments}</small>
        </span>
    </a>
    """

# ------------------------------------------------------------
# Magazines
# ------------------------------------------------------------

magazine_cards = ""

for magazine in magazines:
    title = magazine.get("title") or "（無題のマガジン）"
    note_count = magazine.get("note_count", 0)
    likes = magazine.get("likes", 0)

    magazine_cards += f"""
    <a
        class="magazine-card"
        href="{esc(magazine_url(magazine))}"
        target="_blank"
        rel="noopener noreferrer"
    >
        <div class="magazine-title">
            {esc(title)}
        </div>

        <div class="magazine-meta">
            <span>{note_count}本収録</span>
            <span>♥ {likes}</span>
        </div>
    </a>
    """

if not magazines:
    magazine_cards = """
    <div class="empty-chart">
        マガジンがまだありません。
    </div>
    """

# ------------------------------------------------------------
# Article list
# ------------------------------------------------------------

article_rows = ""

for note in notes:
    title = note.get("title", "")
    published = format_date(note.get("published_at"))
    month = format_month(note.get("published_at"))
    likes = safe_int(note.get("likes"))
    comments = safe_int(note.get("comments"))

    article_rows += f"""
    <article
        class="article-row"
        data-title="{esc(title.lower())}"
        data-month="{esc(month)}"
        data-likes="{likes}"
        data-comments="{comments}"
    >
        <div class="article-date">
            {esc(published)}
        </div>

        <div class="article-main">
            <a
                href="{esc(note_url(note))}"
                target="_blank"
                rel="noopener noreferrer"
                class="article-title"
            >
                {esc(title)}
            </a>
        </div>

        <div class="article-stats">
            <span class="like-stat">
                ♥ {likes}
            </span>

            <span class="comment-stat">
                💬 {comments}
            </span>
        </div>
    </article>
    """

# ------------------------------------------------------------
# Month options
# ------------------------------------------------------------

month_options = ""

for month in reversed(months):
    month_options += f"""
    <option value="{esc(month)}">
        {esc(month)}
    </option>
    """

# ------------------------------------------------------------
# HTML
# ------------------------------------------------------------

html_document = f"""<!DOCTYPE html>

<html lang="ja"><head><meta charset="UTF-8"><script>
(function() {{
    var stored = localStorage.getItem("theme");
    var prefersDark =
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (stored === "dark" || (!stored && prefersDark)) {{
        document.documentElement.classList.add("dark");
    }}
}})();
</script><meta
name="viewport"
content="width=device-width, initial-scale=1.0"

>

<title>{esc(PAGE_TITLE)}</title><link
    rel="icon"
    type="image/svg+xml"
    href="favicon.svg"
><link
    rel="alternate icon"
    href="favicon.ico"
><link
    rel="apple-touch-icon"
    href="favicon-180.png"
><meta
name="description"
content="桜星雨夜のnote活動ログ。記事、スキ、コメント、フォロワー、投稿活動の推移を記録しています。"

>

<meta name="theme-color" content="{BG}"><link
    rel="preconnect"
    href="https://fonts.googleapis.com"
><link
    rel="preconnect"
    href="https://fonts.gstatic.com"
    crossorigin
><link
    rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Noto+Serif+JP:wght@400;500;600&display=swap"
><style>

:root {{
    --bg: {BG};
    --paper: {PAPER};
    --paper-rgb: {PAPER_RGB};
    --ink: {INK};
    --muted: {MUTED};
    --light: {LIGHT};
    --purple: {PURPLE};
    --purple-light: {PURPLE_LIGHT};
    --pink: {PINK};
    --red: {RED};
    --line: {LINE};
    --heat-1: {HEAT_1};
    --heat-2: {HEAT_2};
}}

html.dark {{
    --bg: {DARK_BG};
    --paper: {DARK_PAPER};
    --paper-rgb: {DARK_PAPER_RGB};
    --ink: {DARK_INK};
    --muted: {DARK_MUTED};
    --light: {DARK_LIGHT};
    --purple: {DARK_PURPLE};
    --purple-light: {DARK_PURPLE_LIGHT};
    --pink: {DARK_PINK};
    --red: {DARK_RED};
    --line: {DARK_LINE};
    --heat-1: {DARK_HEAT_1};
    --heat-2: {DARK_HEAT_2};
}}

html {{
    transition:
        background-color 0.3s ease,
        color 0.3s ease;
}}

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    margin: 0;

    overflow-x: hidden;

    background:
        radial-gradient(
            circle at 85% 5%,
            rgba(217, 195, 172, 0.28),
            transparent 26rem
        ),
        radial-gradient(
            circle at 5% 45%,
            rgba(240, 230, 219, 0.75),
            transparent 28rem
        ),
        var(--bg);

    color: var(--ink);

    font-family:
        'Crimson Pro',
        'Noto Serif JP',
        -apple-system,
        BlinkMacSystemFont,
        "Yu Gothic",
        "Hiragino Kaku Gothic ProN",
        serif;

    line-height: 1.7;
}}

a {{
    color: inherit;
}}

.site-shell {{
    width: min(1180px, calc(100% - 40px));
    margin: 0 auto;

    min-width: 0;
}}

.site-header {{
    min-height: 330px;
    padding: 72px 0 48px;

    display: flex;
    align-items: flex-end;

    position: relative;
}}

.theme-toggle {{
    position: absolute;
    top: 28px;
    right: 0;

    appearance: none;

    width: 40px;
    height: 40px;

    display: flex;
    align-items: center;
    justify-content: center;

    background: var(--paper);

    border: 1px solid var(--line);
    border-radius: 50%;

    cursor: pointer;

    z-index: 2;

    transition:
        border-color 0.2s ease,
        transform 0.2s ease;
}}

.theme-toggle:hover {{
    border-color: var(--purple);

    transform: rotate(12deg);
}}

.theme-toggle-icon {{
    font-size: 16px;

    color: var(--purple);

    position: absolute;

    transition:
        opacity 0.2s ease,
        transform 0.2s ease;
}}

.theme-icon-light {{
    opacity: 1;
    transform: scale(1);
}}

.theme-icon-dark {{
    opacity: 0;
    transform: scale(0.5);
}}

html.dark .theme-icon-light {{
    opacity: 0;
    transform: scale(0.5);
}}

html.dark .theme-icon-dark {{
    opacity: 1;
    transform: scale(1);
}}

.site-header::before {{
    content: "";

    position: absolute;

    left: -100px;
    bottom: 35px;

    width: 180px;
    height: 1px;

    background: var(--red);
    opacity: 0.65;
}}

.header-kicker {{
    color: var(--purple);

    font-size: 12px;
    letter-spacing: 0.28em;

    margin-bottom: 14px;

    text-transform: uppercase;
}}

.logo {{
    margin: 0;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-weight: 400;

    font-size: clamp(54px, 9vw, 108px);

    letter-spacing: -0.045em;

    line-height: 0.95;
}}

.logo span {{
    color: var(--purple);
}}

.header-subtitle {{
    margin: 20px 0 0;

    color: var(--muted);

    font-size: 13px;
    letter-spacing: 0.12em;
}}

.header-link {{
    display: inline-block;

    margin-top: 20px;

    color: var(--purple);

    text-decoration: none;

    font-size: 12px;
    letter-spacing: 0.08em;
}}

.header-link:hover {{
    color: var(--red);
}}

.tab-nav {{
    display: flex;

    flex-wrap: wrap;

    gap: 6px;

    margin-bottom: 40px;

    border-bottom: 1px solid var(--line);

    padding-bottom: 0;
}}

.tab-button {{
    appearance: none;

    background: transparent;
    border: 1px solid transparent;
    border-bottom: none;

    border-radius: 4px 4px 0 0;

    padding: 11px 16px;

    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 13px;
    letter-spacing: 0.04em;

    color: var(--muted);

    cursor: pointer;

    transition:
        color 0.2s ease,
        background 0.2s ease,
        border-color 0.2s ease;

    margin-bottom: -1px;
}}

.tab-button:hover {{
    color: var(--purple);
}}

.tab-button.is-active {{
    color: var(--purple);

    background: var(--paper);

    border-color: var(--line);
    border-bottom: 1px solid var(--paper);
}}

.tab-panel {{
    display: none;

    margin: 0 0 40px;
}}

.tab-panel.is-active {{
    display: block;
}}

@media (max-width: 640px) {{
    .tab-nav {{
        flex-wrap: nowrap;

        overflow-x: auto;

        -webkit-overflow-scrolling: touch;

        border-bottom: 1px solid var(--line);
    }}

    .tab-button {{
        flex: 0 0 auto;

        white-space: nowrap;
    }}
}}

.section {{
    margin: 0;
}}

.section-heading {{
    display: flex;

    align-items: baseline;

    gap: 18px;

    margin-bottom: 26px;
}}

.section-number {{
    font-family: 'Crimson Pro', Georgia, serif;

    color: var(--red);

    font-size: 12px;
}}

.section-title {{
    margin: 0;

    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 28px;
    font-weight: 400;

    letter-spacing: 0.02em;
}}

.section-caption {{
    color: var(--muted);

    font-size: 12px;
}}

.stats-grid {{
    display: grid;

    grid-template-columns: repeat(4, 1fr);

    gap: 1px;

    background: var(--line);

    border: 1px solid var(--line);
}}

.stat {{
    background: rgba(var(--paper-rgb), 0.78);

    min-height: 150px;

    padding: 28px;

    display: flex;

    flex-direction: column;
    justify-content: space-between;
}}

.stat-label {{
    font-size: 11px;

    color: var(--muted);

    letter-spacing: 0.15em;
}}

.stat-value {{
    font-family: 'Crimson Pro', Georgia, serif;

    font-size: clamp(34px, 5vw, 52px);

    font-weight: 400;

    line-height: 1;
}}

.stat-unit {{
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Noto Sans JP",
        sans-serif;

    font-size: 12px;

    color: var(--muted);

    margin-left: 4px;
}}

.stat-note {{
    font-size: 11px;

    color: var(--muted);
}}

.dashboard-grid {{
    display: grid;

    grid-template-columns: 1.5fr 1fr;

    gap: 18px;

    min-width: 0;
}}

.panel {{
    background: var(--paper);

    border: 1px solid var(--line);

    padding: 26px;

    min-width: 0;
}}

.panel-title {{
    margin: 0 0 4px;

    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 19px;
    font-weight: 400;
}}

.panel-caption {{
    margin: 0 0 18px;

    color: var(--muted);

    font-size: 11px;
}}

.line-chart {{
    width: 100%;
    height: 280px;

    display: block;
}}

.chart-grid {{
    stroke: var(--line);
    stroke-width: 1;
}}

.chart-axis {{
    fill: var(--muted);
    font-size: 10px;
}}

.empty-chart {{
    min-height: 160px;

    display: grid;
    place-items: center;

    color: var(--muted);

    font-size: 12px;
}}

.bar-chart {{
    height: 210px;
    max-width: 100%;

    display: flex;

    align-items: flex-end;

    gap: 9px;

    overflow-x: auto;
    -webkit-overflow-scrolling: touch;

    padding: 10px 0 4px;
}}

.bar-column {{
    min-width: 30px;

    height: 190px;

    display: flex;

    flex-direction: column;

    align-items: center;
    justify-content: flex-end;
}}

.bar-value {{
    font-size: 10px;

    color: var(--muted);

    margin-bottom: 4px;
}}

.bar {{
    width: 22px;

    background: var(--purple);

    border-radius: 2px 2px 0 0;

    min-height: 4px;

    opacity: 0.8;
}}

.bar-label {{
    margin-top: 8px;

    font-size: 9px;

    color: var(--muted);

    white-space: nowrap;
}}

.streak-stats {{
    display: grid;

    grid-template-columns: 1fr 1fr;

    gap: 1px;

    background: var(--line);

    border: 1px solid var(--line);

    margin-top: 6px;
}}

.streak-stat {{
    background: var(--paper);

    padding: 22px;

    display: flex;

    flex-direction: column;

    gap: 8px;
}}

.streak-value {{
    font-family: 'Crimson Pro', Georgia, serif;

    font-size: clamp(30px, 4.5vw, 42px);

    color: var(--purple);

    line-height: 1;
}}

.streak-unit {{
    font-size: 12px;

    color: var(--muted);

    margin-left: 4px;
}}

.streak-label {{
    font-size: 11px;

    color: var(--muted);
}}

.heatmap-wrap {{
    display: flex;

    gap: 9px;

    align-items: center;
}}

.weekday-labels {{
    width: 18px;
    height: 96px;

    display: flex;

    flex-direction: column;
    justify-content: space-between;

    font-size: 9px;

    color: var(--muted);
}}

.heatmap {{
    display: grid;

    grid-template-rows: repeat(7, 11px);

    grid-auto-flow: column;
    grid-auto-columns: 11px;

    gap: 3px;

    overflow-x: auto;

    padding-bottom: 4px;
}}

.heat-cell {{
    display: block;

    width: 11px;
    height: 11px;

    border-radius: 2px;
}}

.heat-cell.level-0 {{
    background: var(--line);
}}

.heat-cell.level-1 {{
    background: var(--heat-1);
}}

.heat-cell.level-2 {{
    background: var(--heat-2);
}}

.heat-cell.level-3 {{
    background: var(--purple);
}}

.heat-legend {{
    display: flex;

    align-items: center;

    gap: 5px;

    margin-top: 12px;

    color: var(--muted);

    font-size: 9px;
}}

.popular-list {{
    display: flex;

    flex-direction: column;
}}

.momentum-memo {{
    background: var(--paper);

    border: 1px solid var(--line);
    border-left: 3px solid var(--muted);

    padding: 18px 22px;

    margin-top: 18px;
}}

.momentum-memo.momentum-up {{
    border-left-color: var(--purple);
}}

.momentum-memo.momentum-down {{
    border-left-color: var(--red);
}}

.momentum-label {{
    font-size: 10px;

    letter-spacing: 0.1em;

    color: var(--muted);

    text-transform: uppercase;

    margin-bottom: 8px;
}}

.momentum-text {{
    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 15px;

    color: var(--ink);

    line-height: 1.6;
}}

.momentum-sub {{
    margin-top: 8px;

    font-size: 11px;

    color: var(--muted);
}}

.popular-item {{
    display: grid;

    grid-template-columns: 38px 1fr auto;

    gap: 12px;

    align-items: center;

    padding: 15px 0;

    border-bottom: 1px solid var(--line);

    text-decoration: none;
}}

.popular-item:first-child {{
    padding-top: 5px;
}}

.popular-item:last-child {{
    border-bottom: 0;
}}

.popular-rank {{
    font-family: 'Crimson Pro', Georgia, serif;

    color: var(--red);

    font-size: 13px;
}}

.popular-title {{
    font-size: 13px;

    line-height: 1.55;
}}

.popular-stats {{
    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 12px;

    color: var(--purple);

    white-space: nowrap;
}}

.popular-stats small {{
    color: var(--muted);

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        sans-serif;
}}

.magazine-grid {{
    display: grid;

    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));

    gap: 12px;

    margin-top: 6px;

    min-width: 0;
}}

.magazine-card {{
    display: block;

    background: var(--bg);

    border: 1px solid var(--line);

    border-radius: 4px;

    padding: 16px;

    text-decoration: none;

    color: inherit;

    min-width: 0;

    transition:
        border-color 0.2s ease,
        transform 0.2s ease;
}}

.magazine-card:hover {{
    border-color: var(--purple);

    transform: translateY(-2px);
}}

.magazine-title {{
    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 14px;

    line-height: 1.5;

    color: var(--ink);

    overflow-wrap: break-word;
}}

.magazine-meta {{
    display: flex;

    gap: 10px;

    margin-top: 10px;

    font-size: 11px;

    color: var(--muted);
}}

.filters {{
    display: flex;

    gap: 10px;

    flex-wrap: wrap;

    margin-bottom: 14px;
}}

.search-box,
.month-select {{
    height: 42px;

    border: 1px solid var(--line);

    background: rgba(var(--paper-rgb), 0.82);

    color: var(--ink);

    padding: 0 14px;

    font: inherit;

    font-size: 12px;

    outline: none;
}}

.search-box {{
    flex: 1;

    min-width: 220px;
}}

.search-box:focus,
.month-select:focus {{
    border-color: var(--purple);
}}

.article-summary {{
    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 20px;

    margin-bottom: 14px;

    color: var(--muted);

    font-size: 11px;
}}

.article-list {{
    border-top: 1px solid var(--line);
}}

.article-row {{
    display: none;

    grid-template-columns: 120px 1fr 130px;

    gap: 25px;

    align-items: center;

    padding: 21px 8px;

    border-bottom: 1px solid var(--line);

    transition:
        background 0.2s ease,
        padding-left 0.2s ease;
}}

.article-row.is-visible {{
    display: grid;
}}

.article-row:hover {{
    background: rgba(var(--paper-rgb), 0.72);

    padding-left: 14px;
}}

.article-date {{
    color: var(--muted);

    font-family: 'Crimson Pro', Georgia, serif;

    font-size: 12px;
}}

.article-title {{
    text-decoration: none;

    font-size: 14px;

    line-height: 1.6;
}}

.article-title:hover {{
    color: var(--purple);
}}

.article-stats {{
    display: flex;

    justify-content: flex-end;

    gap: 13px;

    color: var(--muted);

    font-size: 11px;

    white-space: nowrap;
}}

.like-stat {{
    color: var(--purple);
}}

.comment-stat {{
    color: var(--muted);
}}

.pagination {{
    display: none;

    justify-content: center;

    align-items: center;

    gap: 8px;

    margin-top: 28px;
}}

.pagination.is-visible {{
    display: flex;
}}

.page-button {{
    min-width: 40px;
    height: 40px;

    padding: 0 10px;

    border: 1px solid var(--line);

    background: rgba(var(--paper-rgb), 0.82);

    color: var(--ink);

    font-family: inherit;

    font-size: 12px;

    cursor: pointer;

    transition:
        border-color 0.2s ease,
        background 0.2s ease,
        color 0.2s ease;
}}

.page-button:hover:not(:disabled) {{
    border-color: var(--purple);

    color: var(--purple);
}}

.page-button.is-active {{
    background: var(--purple);

    border-color: var(--purple);

    color: var(--paper);
}}

.page-button:disabled {{
    opacity: 0.35;

    cursor: default;
}}

.page-ellipsis {{
    min-width: 20px;

    text-align: center;

    color: var(--muted);

    font-size: 12px;
}}

.no-results {{
    display: none;

    padding: 50px;

    text-align: center;

    color: var(--muted);

    font-size: 12px;
}}

.footer {{
    margin-top: 100px;

    padding: 40px 0 70px;

    border-top: 1px solid var(--line);

    display: flex;

    justify-content: space-between;

    gap: 30px;

    color: var(--muted);

    font-size: 10px;

    letter-spacing: 0.08em;
}}

.footer a {{
    color: var(--purple);

    text-decoration: none;
}}

@media (max-width: 800px) {{

    .site-shell {{
        width: min(100% - 28px, 1180px);
    }}

    .site-header {{
        min-height: 260px;

        padding-top: 50px;
    }}

    .theme-toggle {{
        top: 18px;

        width: 34px;
        height: 34px;
    }}

    .stats-grid {{
        grid-template-columns: repeat(2, 1fr);
    }}

    .dashboard-grid {{
        grid-template-columns: 1fr;
    }}

    .article-row {{
        grid-template-columns: 85px 1fr;

        gap: 10px 18px;
    }}

    .article-stats {{
        grid-column: 2;

        justify-content: flex-start;
    }}

}}

@media (max-width: 500px) {{

    .stats-grid {{
        grid-template-columns: 1fr 1fr;
    }}

    .stat {{
        min-height: 125px;

        padding: 20px;
    }}

    .stat-value {{
        font-size: 34px;
    }}

    .article-summary {{
        align-items: flex-start;

        flex-direction: column;

        gap: 3px;
    }}

    .article-row {{
        grid-template-columns: 1fr;

        gap: 5px;

        padding: 17px 3px;
    }}

    .article-stats {{
        grid-column: auto;
    }}

    .pagination {{
        gap: 5px;
    }}

    .page-button {{
        min-width: 36px;
        height: 36px;

        padding: 0 8px;
    }}

    .footer {{
        flex-direction: column;
    }}

}}

</style></head><body><div class="site-shell"><header class="site-header"><div>

    <div class="header-kicker">
        SQUALL / NOTE ARCHIVE
    </div>

    <h1 class="logo">
        NOTE <span>LOG</span>
    </h1>

    <p class="header-subtitle">
        桜星 雨夜 ／ note activity archive
    </p>

    <a
        class="header-link"
        href="{esc(NOTE_URL)}"
        target="_blank"
        rel="noopener noreferrer"
    >
        note.com / squallxxx →
    </a>

</div>

<button
    type="button"
    class="theme-toggle"
    id="themeToggle"
    aria-label="ダークモード切り替え"
>
    <span class="theme-toggle-icon theme-icon-light">☀</span>
    <span class="theme-toggle-icon theme-icon-dark">☾</span>
</button>

</header><main><nav class="tab-nav" id="tabNav">
    <button type="button" class="tab-button" data-tab="overview">01 Overview</button>
    <button type="button" class="tab-button" data-tab="activity">02 Activity</button>
    <button type="button" class="tab-button" data-tab="numbers">03 Numbers</button>
    <button type="button" class="tab-button" data-tab="popular">04 Popular</button>
    <button type="button" class="tab-button" data-tab="articles">05 Articles</button>
</nav><section class="section tab-panel" id="tab-overview" data-tab="overview"><div class="section-heading">

    <span class="section-number">
        01
    </span>

    <h2 class="section-title">
        Overview
    </h2>

    <span class="section-caption">
        記録時点 {esc(updated_label)}
    </span>

</div>

<div class="stats-grid">

    <div class="stat">

        <div class="stat-label">
            ARTICLES
        </div>

        <div class="stat-value">
            {article_count}
            <span class="stat-unit">
                posts
            </span>
        </div>

        <div class="stat-note">
            直近30日：{recent_30_days_posts}本
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            FOLLOWERS
        </div>

        <div class="stat-value">
            {followers}
            <span class="stat-unit">
                people
            </span>
        </div>

        <div class="stat-note">
            following {following}
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            LIKES
        </div>

        <div class="stat-value">
            {total_likes}
            <span class="stat-unit">
                ♥
            </span>
        </div>

        <div class="stat-note">
            average {average_likes} / article
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            COMMENTS
        </div>

        <div class="stat-value">
            {total_comments}
            <span class="stat-unit">
                comments
            </span>
        </div>

        <div class="stat-note">
            average {average_comments} / article
        </div>

    </div>

</div>


<div class="panel" style="margin-top:32px;">

    <h3 class="panel-title">
        Magazines
    </h3>

    <p class="panel-caption">
        マガジン一覧（収録本数順）
    </p>

    <div class="magazine-grid">
        {magazine_cards}
    </div>

</div>

</section><section class="section tab-panel" id="tab-activity" data-tab="activity"><div class="section-heading">

    <span class="section-number">
        02
    </span>

    <h2 class="section-title">
        Activity
    </h2>

    <span class="section-caption">
        書いた量と、その変化
    </span>

</div>


<div class="dashboard-grid">

    <div class="panel">

        <h3 class="panel-title">
            Monthly posts
        </h3>

        <p class="panel-caption">
            月ごとの投稿本数
        </p>

        {monthly_chart}

    </div>


    <div class="panel">

        <h3 class="panel-title">
            Writing rhythm
        </h3>

        <p class="panel-caption">
            直近16週間の投稿密度
        </p>

        {heatmap}

    </div>

</div>


<div
    class="panel"
    style="margin-top:18px;"
>

    <h3 class="panel-title">
        Streaks
    </h3>

    <p class="panel-caption">
        連続投稿の記録（週単位）
    </p>

    <div class="streak-stats">

        <div class="streak-stat">
            <div class="streak-value">
                {longest_streak}
                <span class="streak-unit">週</span>
            </div>
            <div class="streak-label">
                最長連続投稿週
            </div>
        </div>

        <div class="streak-stat">
            <div class="streak-value">
                {current_streak}
                <span class="streak-unit">週</span>
            </div>
            <div class="streak-label">
                現在の連続投稿週
            </div>
        </div>

    </div>

</div>


<div
    class="panel"
    style="margin-top:18px;"
>

    <h3 class="panel-title">
        Weekly pace
    </h3>

    <p class="panel-caption">
        直近12週間の週間投稿本数
    </p>

    {weekly_pace_chart}

</div>

</section><section class="section tab-panel" id="tab-numbers" data-tab="numbers"><div class="section-heading">

    <span class="section-number">
        03
    </span>

    <h2 class="section-title">
        Numbers
    </h2>

    <span class="section-caption">
        記録されている数字の推移
    </span>

</div>


<div class="dashboard-grid">

    <div class="panel">

        <h3 class="panel-title">
            Followers
        </h3>

        <p class="panel-caption">
            フォロワー数の推移
        </p>

        {followers_chart}

    </div>


    <div class="panel">

        <h3 class="panel-title">
            Total likes
        </h3>

        <p class="panel-caption">
            全記事の累計スキ数
        </p>

        {likes_chart}

    </div>

</div>


<div
    class="panel"
    style="margin-top:18px;"
>

    <h3 class="panel-title">
        Article count
    </h3>

    <p class="panel-caption">
        note上の記事総数
    </p>

    {posts_chart}

</div>

</section><section class="section tab-panel" id="tab-popular" data-tab="popular"><div class="section-heading">

    <span class="section-number">
        04
    </span>

    <h2 class="section-title">
        Popular
    </h2>

    <span class="section-caption">
        現在のスキ数が多い記事
    </span>

</div>

<div class="panel popular-list">
    {popular_html}
</div>

{momentum_html}

</section><section
    class="section tab-panel"
    id="tab-articles"
    data-tab="articles"
><div id="articles" class="section-heading">

    <span class="section-number">
        05
    </span>

    <h2 class="section-title">
        Articles
    </h2>

    <span class="section-caption">
        全記事アーカイブ
    </span>

</div>


<div class="filters">

    <input
        id="search"
        class="search-box"
        type="search"
        placeholder="記事タイトルを検索…"
        autocomplete="off"
    >

    <select
        id="monthFilter"
        class="month-select"
    >

        <option value="">
            すべての月
        </option>

        {month_options}

    </select>

</div>


<div class="article-summary">

    <span id="articleCount">
        0件の記事
    </span>

    <span id="pageInfo">
        1 / 1 page
    </span>

</div>


<div
    class="article-list"
    id="articleList"
>

    {article_rows}

</div>


<div
    id="pagination"
    class="pagination"
></div>


<div
    id="noResults"
    class="no-results"
>
    該当する記事がありません。
</div>

</section></main><footer class="footer"><span>
    NOTE LOG / SQUALL
</span>

<span>

    <a
        href="{esc(SITE_URL)}"
        target="_blank"
        rel="noopener noreferrer"
    >
        amexfuri.work
    </a>

    ／

    <a
        href="{esc(NOTE_URL)}"
        target="_blank"
        rel="noopener noreferrer"
    >
        note
    </a>

</span>

</footer></div><script>

(function() {{

    const themeToggle =
        document.getElementById("themeToggle");

    if (themeToggle) {{
        themeToggle.addEventListener("click", function() {{
            const isDark =
                document.documentElement.classList.toggle("dark");

            localStorage.setItem(
                "theme",
                isDark ? "dark" : "light"
            );
        }});
    }}

    const tabButtons = Array.from(
        document.querySelectorAll(".tab-button")
    );

    const tabPanels = Array.from(
        document.querySelectorAll(".tab-panel")
    );

    const validTabs = tabButtons.map(
        function(btn) {{
            return btn.dataset.tab;
        }}
    );

    function activateTab(tabName, options) {{

        options = options || {{}};

        if (validTabs.indexOf(tabName) === -1) {{
            tabName = validTabs[0];
        }}

        tabButtons.forEach(function(btn) {{
            btn.classList.toggle(
                "is-active",
                btn.dataset.tab === tabName
            );
        }});

        tabPanels.forEach(function(panel) {{
            panel.classList.toggle(
                "is-active",
                panel.dataset.tab === tabName
            );
        }});

        if (!options.skipHash) {{
            history.replaceState(
                null,
                "",
                "#" + tabName
            );
        }}

        if (options.scrollTop) {{
            window.scrollTo({{ top: 0, behavior: "instant" }});
        }}

    }}

    tabButtons.forEach(function(btn) {{
        btn.addEventListener("click", function() {{
            activateTab(btn.dataset.tab, {{ scrollTop: true }});
        }});
    }});

    const initialTab =
        (location.hash || "").replace("#", "");

    activateTab(initialTab, {{ skipHash: true }});

    const search =
        document.getElementById("search");

    const monthFilter =
        document.getElementById("monthFilter");

    const rows = Array.from(
        document.querySelectorAll(".article-row")
    );

    const noResults =
        document.getElementById("noResults");

    const pagination =
        document.getElementById("pagination");

    const articleCount =
        document.getElementById("articleCount");

    const pageInfo =
        document.getElementById("pageInfo");


    const perPage = 10;

    let currentPage = 1;

    let filteredRows = [...rows];


    function getFilteredRows() {{

        const query =
            search.value
                .trim()
                .toLowerCase();

        const month =
            monthFilter.value;


        return rows.filter(function(row) {{

            const title =
                row.dataset.title || "";

            const rowMonth =
                row.dataset.month || "";


            const matchesTitle =
                !query ||
                title.includes(query);


            const matchesMonth =
                !month ||
                rowMonth === month;


            return (
                matchesTitle &&
                matchesMonth
            );

        }});

    }}


    function createButton(
        label,
        onClick,
        options = {{}}
    ) {{

        const button =
            document.createElement("button");

        button.type = "button";

        button.className =
            "page-button";


        if (options.active) {{
            button.classList.add("is-active");
        }}


        button.textContent =
            label;


        button.disabled =
            Boolean(options.disabled);


        button.addEventListener(
            "click",
            onClick
        );


        return button;

    }}


    function createEllipsis() {{

        const span =
            document.createElement("span");

        span.className =
            "page-ellipsis";

        span.textContent =
            "…";


        return span;

    }}


    function renderPagination(
        totalPages
    ) {{

        pagination.innerHTML = "";


        if (totalPages <= 1) {{

            pagination.classList.remove(
                "is-visible"
            );

            return;

        }}


        pagination.classList.add(
            "is-visible"
        );


        const previousButton =
            createButton(
                "←",
                function() {{

                    if (currentPage > 1) {{
                        currentPage--;

                        renderArticles();

                        document
                            .getElementById("articles")
                            .scrollIntoView({{
                                behavior: "smooth",
                                block: "start"
                            }});

                    }}

                }},
                {{
                    disabled:
                        currentPage === 1
                }}
            );


        pagination.appendChild(
            previousButton
        );


        const pageNumbers = [];


        if (totalPages <= 7) {{

            for (
                let page = 1;
                page <= totalPages;
                page++
            ) {{
                pageNumbers.push(page);
            }}

        }} else {{

            pageNumbers.push(1);


            if (currentPage > 4) {{
                pageNumbers.push("ellipsis");
            }}


            const start =
                Math.max(
                    2,
                    currentPage - 1
                );

            const end =
                Math.min(
                    totalPages - 1,
                    currentPage + 1
                );


            for (
                let page = start;
                page <= end;
                page++
            ) {{
                pageNumbers.push(page);
            }}


            if (
                currentPage <
                totalPages - 3
            ) {{
                pageNumbers.push("ellipsis");
            }}


            pageNumbers.push(
                totalPages
            );

        }}


        pageNumbers.forEach(function(item) {{

            if (item === "ellipsis") {{

                pagination.appendChild(
                    createEllipsis()
                );

                return;

            }}


            const pageButton =
                createButton(
                    String(item),
                    function() {{

                        currentPage = item;

                        renderArticles();

                        document
                            .getElementById("articles")
                            .scrollIntoView({{
                                behavior: "smooth",
                                block: "start"
                            }});

                    }},
                    {{
                        active:
                            currentPage === item
                    }}
                );


            pagination.appendChild(
                pageButton
            );

        }});


        const nextButton =
            createButton(
                "→",
                function() {{

                    if (
                        currentPage <
                        totalPages
                    ) {{
                        currentPage++;

                        renderArticles();

                        document
                            .getElementById("articles")
                            .scrollIntoView({{
                                behavior: "smooth",
                                block: "start"
                            }});

                    }}

                }},
                {{
                    disabled:
                        currentPage === totalPages
                }}
            );


        pagination.appendChild(
            nextButton
        );

    }}


    function renderArticles() {{

        const total =
            filteredRows.length;


        const totalPages =
            Math.max(
                1,
                Math.ceil(
                    total / perPage
                )
            );


        if (
            currentPage >
            totalPages
        ) {{
            currentPage =
                totalPages;
        }}


        const startIndex =
            (currentPage - 1)
            * perPage;


        const endIndex =
            startIndex + perPage;


        const visibleRows =
            filteredRows.slice(
                startIndex,
                endIndex
            );


        rows.forEach(function(row) {{

            row.classList.remove(
                "is-visible"
            );

        }});


        visibleRows.forEach(function(row) {{

            row.classList.add(
                "is-visible"
            );

        }});


        noResults.style.display =
            total === 0
                ? "block"
                : "none";


        articleCount.textContent =
            total === 0
                ? "0件の記事"
                : `${{total}}件の記事`;


        pageInfo.textContent =
            total === 0
                ? "0 / 0 page"
                : `${{currentPage}} / ${{totalPages}} page`;


        renderPagination(
            totalPages
        );

    }}


    function filterArticles() {{

        filteredRows =
            getFilteredRows();


        currentPage = 1;


        renderArticles();

    }}


    search.addEventListener(
        "input",
        filterArticles
    );


    monthFilter.addEventListener(
        "change",
        filterArticles
    );


    renderArticles();

}})();

</script></body>
</html>
"""
# ------------------------------------------------------------
# Write
# ------------------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:
    f.write(html_document)

print(f"HTML generated: {OUTPUT_FILE}")
print(f"Articles: {article_count}")
print(f"Followers: {followers}")
print(f"Likes: {total_likes}")
print(f"Comments: {total_comments}")
