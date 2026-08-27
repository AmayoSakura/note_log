import json
import time
import urllib.request
from datetime import datetime, timezone

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


def fetch_json(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_creator():
    url = f"{BASE_URL}/{USERNAME}"
    data = fetch_json(url)["data"]

    return {
        "nickname": data.get("nickname"),
        "urlname": data.get("urlname"),
        "followerCount": data.get("followerCount"),
        "followingCount": data.get("followingCount"),
        "noteCount": data.get("noteCount"),
        "magazineCount": data.get("magazineCount"),
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

        # note側に負荷をかけないよう少し待つ
        time.sleep(1.0)

    return all_notes


def main():
    print("noteデータ取得開始")
    print()

    creator = get_creator()

    print(f"ユーザー: {creator['nickname']}")
    print(f"フォロワー: {creator['followerCount']}")
    print(f"記事数: {creator['noteCount']}")
    print()

    notes = get_notes()

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "creator": creator,
        "notes": notes,
    }

    with open("note_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print(f"取得完了: {len(notes)}件")
    print("note_data.json に保存しました")


if __name__ == "__main__":
    main()