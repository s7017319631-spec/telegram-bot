# set_webhook.py — запустить один раз локально (или в Render Shell) после деплоя
import requests
import config

webhook_url = f"{config.WEBHOOK_BASE_URL}/telegram-webhook/{config.BOT_TOKEN}"

resp = requests.get(
    f"https://api.telegram.org/bot{config.BOT_TOKEN}/setWebhook",
    params={"url": webhook_url, "drop_pending_updates": True},
)
print(resp.status_code, resp.json())

info = requests.get(f"https://api.telegram.org/bot{config.BOT_TOKEN}/getWebhookInfo")
print(info.json())
