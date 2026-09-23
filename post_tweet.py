import os
import random
import requests
from bs4 import BeautifulSoup
import feedparser
import tweepy
from google import genai

# --------------------------------------------------
# 1. 各種APIキーの設定
# --------------------------------------------------
api_key = os.environ.get("X_API_KEY")
api_secret = os.environ.get("X_API_KEY_SECRET")
access_token = os.environ.get("X_ACCESS_TOKEN")
access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

GOOGLE_ALERT_RSS_URL = "https://news.google.com/rss/search?q=脱炭素+OR+カーボンニュートラル+OR+再生可能エネルギー+OR+水素社会推進法+OR+水素+OR+資源エネルギー庁+OR+ネットゼロ+OR+SAF+OR+日本有機資源協会+OR+地球温暖化対策推進法+OR+炭素税+OR+大気汚染法&hl=ja&gl=JP&ceid=JP:ja"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# --------------------------------------------------
# 2. Googleアラートからニュースを1件取得
# --------------------------------------------------
print("Googleアラートのニュースを取得中...")
feed = feedparser.parse(GOOGLE_ALERT_RSS_URL)

if not feed.entries:
    print("ニュースが見つかりませんでした。")
    exit()

selected_entry = random.choice(feed.entries)
news_title = selected_entry.title
news_link = selected_entry.link

if "url=" in news_link:
    news_link = news_link.split("url=")[1].split("&")[0]

print(f"選択されたニュース: {news_title}")
print(f"URL: {news_link}")

# --------------------------------------------------
# 3. 本文の抽出
# --------------------------------------------------
news_text = ""
try:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(news_link, headers=headers, timeout=10)
    response.encoding = response.apparent_encoding
    
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = soup.find_all("p")
    news_text = "\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
except Exception as e:
    print(f"本文取得スキップ: {e}")

if not news_text:
    news_text = news_title

# --------------------------------------------------
# 4. Gemini AIによる要約（文字数を厳格化）
# --------------------------------------------------
print("Gemini AIでニュースを要約中...")

prompt = f"""
以下のビジネスニュースを読み、Xに投稿するための要約を作成してください。

【厳格な制約条件】
- 必ず「70文字〜130文字以内」で完結させてください。
- 1文または2文の簡潔な要約にしてください。
- 最後に自戒的なメッセージをポピュリズム的なトーンで入れてください。
- 友達や親しい人への言葉遣いみたいに、「だね」「だよね」のような終助詞を用いた表現にしてください。
- ハッシュタグや絵文字、URLは含めないでください。

【ニュース内容】
{news_text[:2000]}
"""

try:
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    summary_text = response.text.strip()
except Exception as e:
    print(f"AI要約エラー: {e}")
    summary_text = news_title

# 念のため75文字を超えていたら末尾をカット
if len(summary_text) > 75:
    summary_text = summary_text[:72] + "..."

print(f"AIが作成した要約:\n{summary_text}")

# --------------------------------------------------
# 5. Xにポスト
# --------------------------------------------------
tweet_text = f"{summary_text}\n\n{news_link}"

x_client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

try:
    x_client.create_tweet(text=tweet_text)
    print("---------------------------------------------")
    print("★AI要約付きニュースの自動投稿に成功しました！")
    print("---------------------------------------------")
except Exception as e:
    print(f"Xへの投稿でエラーが発生しました: {e}")




