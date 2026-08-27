import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USERNAME = "squallxxx"

BASE_URL = "https://note.com/api/v2/creators"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

DATA_DIR = Path("data")
DAILY_STATS_FILE = DATA_DIR / "daily_stats.json"
ARTICLE_HISTORY_FILE = DATA_DIR / "article_history.json"


def fetch_json(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_creator():
    url = f"{BASE_URL}/{USERNAME}"
    data = fetch_json(url)["data"]

    return {
        "nickname": data.get("nickname"),
        "urlname": data.get("urlname"),
        "followerCount": data.get("followerCount", 0),
        "followingCount": data.get("followingCount", 0),
        "noteCount": data.get("noteCount", 0),
        "magazineCount": data.get("magazineCount", 0),
    }


def get_notes():
    all_notes = []

    for page in range(1, 101):
        url = f"{BASE_URL}/{USERNAME}/contents?kind=note&page={page}"

        data = fetch_json(url)["data"]
        contents = data.get("contents", [])

        if not contents:
            break

        for note in contents:
            all_notes.append({
                "id": note.get("id"),
                "key": note.get("key"),
                "title": note.get("name"),
                "published_at": note.get("publishAt"),
                "likes": note.get("likeCount", 0),
                "comments": note.get("commentCount", 0),
                "price": note.get("price", 0),
                "type": note.get("type"),
            })

        print(f"記事取得: page {page} / 累計 {len(all_notes)}件")

        if data.get("isLastPage"):
            break

        time.sleep(1.0)

    return all_notes


def save_daily_stats(creator, notes, today):
    history = load_json(DAILY_STATS_FILE, [])

    total_likes = sum(note["likes"] for note in notes)
    total_comments = sum(note["comments"] for note in notes)

    today_data = {
        "date": today,
        "followers": creator["followerCount"],
        "following": creator["followingCount"],
        "note_count": creator["noteCount"],
        "total_likes": total_likes,
        "total_comments": total_comments,
    }

    # 同じ日に何回実行しても、その日の記録は1件だけにする
    history = [
        item for item in history
        if item.get("date") != today
    ]

    history.append(today_data)

    history.sort(key=lambda item: item["date"])

    save_json(DAILY_STATS_FILE, history)


def save_article_history(notes, today):
    history = load_json(ARTICLE_HISTORY_FILE, {})

    for note in notes:
        article_key = note["key"]

        if not article_key:
            continue

        if article_key not in history:
            history[article_key] = {
                "title": note["title"],
                "published_at": note["published_at"],
                "history": [],
            }

        article = history[article_key]

        # タイトル変更などがあっても最新情報に更新
        article["title"] = note["title"]
        article["published_at"] = note["published_at"]

        # 同じ日の記録は上書き
        article["history"] = [
            item for item in article["history"]
            if item.get("date") != today
        ]

        article["history"].append({
            "date": today,
            "likes": note["likes"],
            "comments": note["comments"],
        })

        article["history"].sort(key=lambda item: item["date"])

    save_json(ARTICLE_HISTORY_FILE, history)


def main():
    print("noteデータ取得開始")
    print()

    creator = get_creator()

    print(f"ユーザー: {creator['nickname']}")
    print(f"フォロワー: {creator['followerCount']}")
    print(f"記事数: {creator['noteCount']}")
    print()

    notes = get_notes()

    # 日本時間で今日の日付を記録
    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")

    # 最新データ
    result = {
        "fetched_at": now.isoformat(),
        "creator": creator,
        "notes": notes,
    }

    with open("note_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 毎日の履歴
    save_daily_stats(creator, notes, today)
    save_article_history(notes, today)

    print()
    print(f"取得完了: {len(notes)}件")
    print("note_data.json を更新しました")
    print("data/daily_stats.json に履歴を保存しました")
    print("data/article_history.json に記事履歴を保存しました")


if __name__ == "__main__":
    main()
