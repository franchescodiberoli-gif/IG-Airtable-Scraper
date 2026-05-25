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

def _download_video(dl_link, reel_id, rapidapi_key):
    video_bytes = None

    # Intento 1: link CDN directo
    try:
        r = requests.get(dl_link, timeout=20)
        r.raise_for_status()
        video_bytes = BytesIO(r.content)
        video_bytes.name = f"{reel_id}.mp4"
        video_bytes.seek(0)
        logging.info(f"[Intento 1 OK] {reel_id}")
    except Exception as e:
        logging.warning(f"[Intento 1 FAIL] {reel_id}: {e}")

    # Intento 2: RapidAPI link fresco
    if not video_bytes and rapidapi_key:
        try:
            rapid_headers = {
                "x-rapidapi-key": rapidapi_key,
                "x-rapidapi-host": "real-time-instagram-scraper-api1.p.rapidapi.com"
            }
            resp2 = requests.get(
                "https://real-time-instagram-scraper-api1.p.rapidapi.com/v1/post_info",
                headers=rapid_headers,
                params={"code_or_id_or_url": reel_id},
                timeout=15
            )
            resp2.raise_for_status()
            data2 = resp2.json().get("data", {})
            vid2  = max(data2.get("video_versions", []), key=lambda v: v.get("height", 0), default={})
            fresh_url = vid2.get("url", "")
            if not fresh_url:
                raise ValueError("No URL de video")
            r2 = requests.get(fresh_url, timeout=20)
            r2.raise_for_status()
            video_bytes = BytesIO(r2.content)
            video_bytes.name = f"{reel_id}.mp4"
            video_bytes.seek(0)
            logging.info(f"[Intento 2 OK] {reel_id}")
        except Exception as e2:
            logging.warning(f"[Intento 2 FAIL] {reel_id}: {e2}")

    # Intento 3: yt-dlp con link de Instagram
    if not video_bytes:
        try:
            import yt_dlp
            ydl_opts = {"quiet": True, "no_warnings": True, "format": "best[ext=mp4]/best"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.instagram.com/reel/{reel_id}/", download=False)
            formats   = info.get("formats") or []
            fresh_url = info.get("url") or (formats[-1].get("url") if formats else "")
            if not fresh_url:
                raise ValueError("yt-dlp no extrajo URL")
            r3 = requests.get(fresh_url, timeout=30)
            r3.raise_for_status()
            video_bytes = BytesIO(r3.content)
            video_bytes.name = f"{reel_id}.mp4"
            video_bytes.seek(0)
            logging.info(f"[Intento 3 OK] {reel_id}")
        except Exception as e3:
            logging.warning(f"[Intento 3 FAIL] {reel_id}: {e3}")

    return video_bytes

def send_gave_to_model_videos(api_key, base_id):
    settings = records_to_dataframe(fetch_table_records(api_key, base_id, "🔑 Automation settings"))

    try:
        bot_token    = settings.loc[settings["Name"]=="TELEGRAM_BOT_API_KEY",     "Value"].iat[0]
        personal_id  = settings.loc[settings["Name"]=="TELEGRAM_PERSONAL_CHAT_ID","Value"].iat[0]
        rapidapi_key = settings.loc[settings["Name"]=="RAPIDAPI_KEY",             "Value"].iat[0]
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
        rid     = reel["id"]
        flds    = reel.get("fields", {})
        code    = flds.get("🤖 Reel ID", "")
        dl_link = flds.get("⬇️ Download link", "")
        views   = flds.get("👀 Views", 0)
        likes   = flds.get("👍 Like count", 0)
        comments= flds.get("💬 Comment count", 0)
        caption = flds.get("📒 Caption", "")
        vir_pct = flds.get("Virality score", 0) * 100

        logging.info(f"Processing reel {rid} ({code})")
        video_bytes = _download_video(dl_link, code, rapidapi_key)

        base_text = (
            f"✅ Reel enviado al modelo\n\n"
            f"📊 Virality: +{vir_pct:.2f}% sobre promedio\n"
            f"👀 Views: {views}\n"
            f"👍 Likes: {likes}\n"
            f"💬 Comments: {comments}\n\n"
            f"🔗 https://www.instagram.com/reel/{code}\n\n"
            f"💬 {caption}"
        )

        if video_bytes:
            try:
                rv = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendVideo",
                    data={"chat_id": personal_chat_id, "caption": base_text},
                    files={"video": (video_bytes.name, video_bytes, "video/mp4")}
                )
                rv.raise_for_status()
                logging.info(f"sendVideo OK para reel {rid}")
            except Exception as e:
                logging.error(f"sendVideo failed {rid}: {e}")
                video_bytes = None

        if not video_bytes:
            try:
                rt = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={"chat_id": personal_chat_id, "text": base_text + "\n\n⚠️ Video link expired."}
                )
                rt.raise_for_status()
                logging.info(f"sendMessage OK (sin video) para reel {rid}")
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
            logging.info(f"Marcado Enviado y desmarcado Gave to the Model para {rid}")
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
