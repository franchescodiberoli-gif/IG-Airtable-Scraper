import requests
import pandas as pd
import logging
import os
from io import BytesIO
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [WATCHER]: %(message)s"
)

def load_config():
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        raise RuntimeError("Missing environment variables")
    return {"api_key": api_key, "base_id": base_id}

def fetch_table_records(api_key, base_id, table_name):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"https://api.airtable.com/v0/{base_id}/{quote(table_name)}"
    all_records = []
    offset = None
    while True:
        params = {}
        if offset:
            params["offset"] = offset
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        all_records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return all_records

def records_to_dataframe(records):
    rows = [rec.get("fields", {}) for rec in records]
    return pd.DataFrame(rows)

def _download_video(ig_share_link, cdn_link, reel_id):
    """
    Orden de intentos (sin RapidAPI para no consumir creditos):
    1. yt-dlp con link permanente de Instagram (gratis, no expira)
    2. CDN directo como respaldo
    """
    video_bytes = None

    # Intento 1: yt-dlp con link permanente de Instagram
    if ig_share_link:
        try:
            import yt_dlp
            logging.info(f"[Intento 1] yt-dlp con {ig_share_link}")
            ydl_opts = {"quiet": True, "no_warnings": True, "format": "best[ext=mp4]/best"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(ig_share_link, download=False)
            formats   = info.get("formats") or []
            fresh_url = info.get("url") or (formats[-1].get("url") if formats else "")
            if not fresh_url:
                raise ValueError("yt-dlp no extrajo URL")
            r = requests.get(fresh_url, timeout=30)
            r.raise_for_status()
            video_bytes = BytesIO(r.content)
            video_bytes.name = f"{reel_id}.mp4"
            video_bytes.seek(0)
            logging.info(f"[Intento 1 OK] yt-dlp exitoso para {reel_id}")
        except Exception as e:
            logging.warning(f"[Intento 1 FAIL] yt-dlp: {e}")

    # Intento 2: CDN directo
    if not video_bytes and cdn_link:
        try:
            logging.info(f"[Intento 2] CDN directo para {reel_id}")
            r = requests.get(cdn_link, timeout=20)
            r.raise_for_status()
            video_bytes = BytesIO(r.content)
            video_bytes.name = f"{reel_id}.mp4"
            video_bytes.seek(0)
            logging.info(f"[Intento 2 OK] CDN para {reel_id}")
        except Exception as e:
            logging.warning(f"[Intento 2 FAIL] CDN: {e}")

    return video_bytes

def send_gave_to_model_videos(api_key, base_id):
    settings = records_to_dataframe(fetch_table_records(api_key, base_id, "🔑 Automation settings"))

    try:
        bot_token    = settings.loc[settings["Name"]=="TELEGRAM_BOT_API_KEY",     "Value"].iat[0]
        personal_id  = settings.loc[settings["Name"]=="TELEGRAM_PERSONAL_CHAT_ID","Value"].iat[0]
    except Exception as e:
        logging.error(f"Missing settings: {e}")
        return

    try:
        personal_chat_id = int(personal_id)
    except ValueError:
        personal_chat_id = personal_id

    reels   = fetch_table_records(api_key, base_id, "🎥 Agency Reels")
    to_send = [r for r in reels if r.get("fields", {}).get("Gave to the Model") == True]
    logging.info(f"Found {len(to_send)} reels marked 'Gave to the Model'")

    for reel in to_send:
        rid          = reel["id"]
        flds         = reel.get("fields", {})
        code         = flds.get("🤖 Reel ID", "")
        cdn_link     = flds.get("⬇️ Download link", "")
        ig_share     = f"https://www.instagram.com/reel/{code}/"

        logging.info(f"Processing reel {rid} ({code})")
        video_bytes = _download_video(ig_share, cdn_link, code)

        if video_bytes:
            # Manda SOLO el video, sin texto ni caption
            try:
                rv = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendVideo",
                    data={"chat_id": personal_chat_id},
                    files={"video": (video_bytes.name, video_bytes, "video/mp4")}
                )
                rv.raise_for_status()
                logging.info(f"sendVideo OK para reel {rid}")
            except Exception as e:
                logging.error(f"sendVideo failed {rid}: {e}")
                video_bytes = None

        if not video_bytes:
            # Si no hay video manda solo el link de Instagram
            try:
                rt = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={"chat_id": personal_chat_id, "text": ig_share}
                )
                rt.raise_for_status()
                logging.info(f"sendMessage link OK para reel {rid}")
            except Exception as e:
                logging.error(f"sendMessage failed {rid}: {e}")

        # Desmarcar Gave to the Model y marcar Enviado
        try:
            patch_url = f"https://api.airtable.com/v0/{base_id}/{quote('🎥 Agency Reels')}"
            payload = {"records": [{"id": rid, "fields": {
                "Gave to the Model": False,
                "📤 Enviado": True
            }}]}
            rp = requests.patch(patch_url, json=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            rp.raise_for_status()
            logging.info(f"Marcado Enviado para {rid}")
        except Exception as e:
            logging.error(f"Failed to update flags for {rid}: {e}")

def main():
    try:
        cfg = load_config()
        send_gave_to_model_videos(cfg["api_key"], cfg["base_id"])
    except Exception as e:
        logging.error(f"Watcher error: {e}")

if __name__ == "__main__":
    main()
