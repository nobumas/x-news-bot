import os
import random
import requests
from bs4 import BeautifulSoup
import feedparser
import tweepy
from google import genai

# --------------------------------------------------
# 1. 各種APIキー・鍵の設定
# --------------------------------------------------
# X (Twitter) の鍵（環境変数から取得）
api_key = os.environ.get("X_API_KEY")
api_secret = os.environ.get("X_API_KEY_SECRET")
access_token = os.environ.get("X_ACCESS_TOKEN")
access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

# GoogleアラートのRSSフィードURL
GOOGLE_ALERT_RSS_URL = "https://news.google.com/rss/search?q=脱炭素+OR+カーボンニュートラル+OR+再生可能エネルギー+OR+水素社会推進法+OR+水素+OR+資源エネルギー庁+OR+ネットゼロ+OR+SAF+OR+日本有機資源協会+OR+地球温暖化対策推進法+OR+炭素税+OR+大気汚染法&hl=ja&gl=JP&ceid=JP:ja"

# Gemini APIのキー（環境変数から取得）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# --------------------------------------------------
# 2. Googleアラートからニュースをランダムに1件取得
# --------------------------------------------------
print("Googleアラートのニュースを取得中...")
feed = feedparser.parse(GOOGLE_ALERT_RSS_URL)

if not feed.entries:
    print("ニュースが見つかりませんでした。Googleアラートの設定を確認してください。")
    exit()

# 配信されたニュースの中からランダムに1件選択
selected_entry = random.choice(feed.entries)
news_title = selected_entry.title
news_link = selected_entry.link

# Googleアラートのリンクは転送URLになっている場合があるため、元のURLを抽出
if "url=" in news_link:
    news_link = news_link.split("url=")[1].split("&")[0]

print(f"選択されたニュース: {news_title}")
print(f"URL: {news_link}")

# --------------------------------------------------
# 3. ニュースサイトから本文テキストを抽出
# --------------------------------------------------
news_text = ""
try:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(news_link, headers=headers, timeout=10)
    response.encoding = response.apparent_encoding
    
    soup = BeautifulSoup(response.text, "html.parser")
    # 不要なナビゲーションやフッターを排除し、段落(pタグ)からテキストを抽出
    paragraphs = soup.find_all("p")
    news_text = "\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
except Exception as e:
    print(f"ニュース本文の取得に失敗しました（タイトルのみで要約します）: {e}")

# 本文が取れなかった場合は、タイトルを本文の代わりにする
if not news_text:
    news_text = news_title

# --------------------------------------------------
# 4. Gemini AIを使ってニュースを要約する
# --------------------------------------------------
print("Gemini AIでニュースを要約中...")

# AIへの指示文（プロンプト）
prompt = f"""
以下のビジネスニュースを読み、X（旧Twitter）に投稿するための要約を作成してください。

【制約条件】
- 文字数は「80文字〜100文字程度」に収めてください。
- ビジネスパーソンが通勤時間などにサクッと読んで役立つ、客観的で簡潔なトーン（〜です、〜ます等）にしてください。
- ハッシュタグや絵文字は含めないでください。

【ニュース内容】
{news_text[:2000]}
"""

try:
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    summary_text = response.text.strip()
    print(f"AIが作成した要約:\n{summary_text}")
except Exception as e:
    print(f"AI要約でエラーが発生しました: {e}")
    summary_text = news_title

# --------------------------------------------------
# 5. Xに自動投稿文を組み立ててポストする
# --------------------------------------------------
# Xの140文字制限に収まるように最終調整
tweet_text = f"{summary_text}\n\n{news_link}"

# XのAPIに接続
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