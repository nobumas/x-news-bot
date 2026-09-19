import os
import random
import requests
from bs4 import BeautifulSoup
import feedparser
import tweepy
from google import genai

# --------------------------------------------------
# 1. 各種APIキーの設定（既存の環境変数をそのまま共用）
# --------------------------------------------------
api_key = os.environ.get("X_API_KEY")
api_secret = os.environ.get("X_API_KEY_SECRET")
access_token = os.environ.get("X_ACCESS_TOKEN")
access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

# 健康・長寿・予防医学に関するGoogleニュースRSS
GOOGLE_ALERT_RSS_URL = "https://news.google.com/rss/search?q=健康寿命+OR+老化研究+OR+抗老化+OR+予防医学+OR+オートファジー+OR+NMN+OR+認知症予防+OR+長寿科学+OR+アンチエイジング+OR+ハーバード大学+研究+OR+健康長寿&hl=ja&gl=JP&ceid=JP:ja"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# --------------------------------------------------
# 2. ニュースを1件取得
# --------------------------------------------------
print("健康・長寿関連のニュースを取得中...")
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
# 4. Gemini AIによる要約（50〜60代向けトーン）
# --------------------------------------------------
print("Gemini AIでニュースを要約中...")

prompt = f"""
以下の健康・医療・長寿に関する最新ニュース・研究情報を読み、X向けの投稿文を作成してください。

【ターゲット読者】
- 50代〜60代の知的好奇心が高いビジネスパーソンやアクティブシニア

【厳格な制約条件】
- 必ず「50文字〜70文字以内」で完結させてください。
- 「最新研究の要点」や「日常生活や健康寿命へのヒント」がサクッと伝わる、落ち着いた知的なトーン（〜です、〜とされています等）にしてください。
- 煽り文句、ハッシュタグ、絵文字、URLは含めないでください。

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

# 文字数オーバー対策（75文字超でカット）
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
    print("★健康・長寿ニュースの自動投稿に成功しました！")
    print("---------------------------------------------")
except Exception as e:
    print(f"Xへの投稿でエラーが発生しました: {e}")