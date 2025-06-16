from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from googletrans import Translator
import requests
import os
import datetime

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()

    # 翻譯中文地名成英文
    translator = Translator()
    translated = translator.translate(user_text, dest="en")
    city_en = translated.text

    # 呼叫天氣 API 查詢天氣
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_en}&appid={WEATHER_API_KEY}&units=metric&lang=zh_tw"
    response = requests.get(weather_url)
    
    if response.status_code == 200:
        data = response.json()
        city_name = data["name"]
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        pop = data.get("pop", 0) * 100  # 若無降雨機率則為 0

        today = datetime.datetime.now().strftime("%m/%d")
        reply_text = f"{today} {city_name} 天氣：{weather}\n溫度：{temp}°C\n降雨機率：{pop:.0f}%"
    else:
        reply_text = f"無法查詢「{user_text}」的天氣，請確認地名是否正確。"

    # 回傳結果給用戶
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    app.run()

