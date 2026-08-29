import json
import time
import urllib.error
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


def fetch_json(url, max_retries=3):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            request = urllib.request.Request(url, headers=HEADERS)

            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last_error = e

            if attempt < max_retries:
                wait = 3 * attempt
                print(
                    f"通信エラー（{attempt}/{max_retries}回目）: {e} "
                    f"/ {wait}秒待って再試行します"
                )
                time.sleep(wait)
            else:
                print(f"通信エラー（最終試行失敗）: {e}")

    raise last_error


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
    completed = False

    for page in range(1, 101):
        url = f"{BASE_URL}/{USERNAME}/contents?kind=note&page={page}"

        try:
            data = fetch_json(url)["data"]
        except Exception as e:
            print(
                f"記事取得でエラー発生（page {page}）: {e} "
                f"/ ここまでに取得した{len(all_notes)}件で打ち切ります"
            )
            break

        contents = data.get("contents", [])

        if not contents:
            completed = True
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
            completed = True
            break

        time.sleep(1.5)

    return all_notes, completed


def get_magazines():
    all_magazines = []

    for page in range(1, 101):
        url = f"{BASE_URL}/{USERNAME}/contents?kind=magazine&page={page}"

        try:
            data = fetch_json(url)["data"]
        except urllib.error.HTTPError as e:
            # マガジン取得に失敗しても記事データ収集自体は止めない
            body = ""
            try:
                body = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            print(
                f"マガジン取得でエラー発生（page {page}）: "
                f"HTTP {e.code} {e.reason} / body: {body}"
            )
            break
        except Exception as e:
            print(f"マガジン取得でエラー発生（page {page}）: {e}")
            break

        contents = data.get("contents", [])

        if not contents:
            break

        for magazine in contents:
            all_magazines.append({
                "id": magazine.get("id"),
                "key": magazine.get("key"),
                "title": magazine.get("name"),
                "description": magazine.get("description"),
                "note_count": (
                    magazine.get("noteCount")
                    or magazine.get("notesCount")
                    or 0
                ),
                "likes": magazine.get("likeCount", 0),
                "is_default": magazine.get("isDefault", False),
                "updated_at": magazine.get("updatedAt"),
            })

        print(f"マガジン取得: page {page} / 累計 {len(all_magazines)}件")

        if data.get("isLastPage"):
            break

        time.sleep(1.5)

    return all_magazines


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

    notes, completed = get_notes()

    print()

    if not completed:
        previous = load_json(Path("note_data.json"), {})
        previous_notes = previous.get("notes", [])

        fetched_ids = {n.get("id") for n in notes}

        missing_notes = [
            n for n in previous_notes
            if n.get("id") not in fetched_ids
        ]

        if missing_notes:
            print(
                f"記事取得が途中で打ち切られたため、"
                f"前回データから{len(missing_notes)}件を補完します"
            )
            notes = notes + missing_notes

    try:
        magazines = get_magazines()
    except Exception as e:
        print(f"マガジン取得に失敗したため、マガジンデータなしで続行します: {e}")
        magazines = []

    # 日本時間で今日の日付を記録
    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")

    # 最新データ
    result = {
        "fetched_at": now.isoformat(),
        "creator": creator,
        "notes": notes,
        "magazines": magazines,
    }

    with open("note_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 毎日の履歴
    save_daily_stats(creator, notes, today)
    save_article_history(notes, today)

    print()
    print(f"取得完了: {len(notes)}件（記事取得{'完走' if completed else '途中打ち切り、前回データで補完'}）")
    print(f"マガジン取得完了: {len(magazines)}件")
    print("note_data.json を更新しました")
    print("data/daily_stats.json に履歴を保存しました")
    print("data/article_history.json に記事履歴を保存しました")


if __name__ == "__main__":
    main()
