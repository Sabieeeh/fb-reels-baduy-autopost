import os
import io
import re
import json
import requests
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
QUEUE_FOLDER_ID = os.environ["GDRIVE_QUEUE_FOLDER_ID"]
DONE_FOLDER_ID = os.environ["GDRIVE_DONE_FOLDER_ID"]
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

LYNK_URL = "https://lynk.id/sabihnu/yk9lpo4voy5w/checkout"


def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def get_next_video(service):
    query = (
        f"'{QUEUE_FOLDER_ID}' in parents and "
        "mimeType contains 'video/' and trashed = false"
    )
    results = (
        service.files()
        .list(
            q=query,
            orderBy="name asc",
            pageSize=1,
            fields="files(id, name, size)",
        )
        .execute()
    )
    files = results.get("files", [])
    return files[0] if files else None


def download_video(service, file_id, local_path):
    request = service.files().get_media(fileId=file_id)
    with io.FileIO(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def move_to_done(service, file_id):
    file_meta = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file_meta.get("parents", []))
    service.files().update(
        fileId=file_id,
        addParents=DONE_FOLDER_ID,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


def generate_viral_caption(filename):
    clean_title = os.path.splitext(filename)[0]
    clean_title = re.sub(r"^\d+[\s_-]*", "", clean_title).replace("_", " ").strip()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Buatkan caption Facebook Reels yang memancing interaksi tinggi dan berpotensi viral berdasarkan topik video dokumenter Baduy berikut:

Topik Video: "{clean_title}"

Aturan wajib:
1. Baris 1 (HOOK): Maksimal 12 kata, memicu rasa penasaran atau fakta mengejutkan agar orang berhenti scroll.
2. Paragraf 2 (CERITA SINGKAT): 2-3 kalimat padat yang menjelaskan konteks budaya/aturan adat Baduy secara autentik dan menggugah diskusi di kolom komentar (akhiri dengan 1 pertanyaan pemancing komentar).
3. Baris 3 (CTA): Ajak penonton yang ingin berkunjung mandiri ke Baduy Luar & Dalam tanpa nyasar untuk membaca panduan lengkapnya di: {LYNK_URL}
4. Baris Terakhir: Berikan 4 hashtag paling relevan (#Baduy #BaduyDalam #BudayaNusantara #WisataBanten).
5. Jangan gunakan tanda kutip pembuka/penutup atau kata pengantar apa pun. Langsung tulis isi caption siap posting."""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def upload_facebook_reel(video_path, caption):
    base_url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/video_reels"

    init_res = requests.post(
        base_url,
        data={
            "upload_phase": "start",
            "access_token": FB_PAGE_ACCESS_TOKEN,
        },
        timeout=30,
    ).json()

    if "video_id" not in init_res:
        raise RuntimeError(f"Gagal start sesi Reels FB: {init_res}")

    video_id = init_res["video_id"]
    upload_url = init_res["upload_url"]
    file_size = os.path.getsize(video_path)

    with open(video_path, "rb") as f:
        upload_res = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {FB_PAGE_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size),
            },
            data=f,
            timeout=300,
        ).json()

    if not upload_res.get("success"):
        raise RuntimeError(f"Gagal upload binary video: {upload_res}")

    finish_res = requests.post(
        base_url,
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": FB_PAGE_ACCESS_TOKEN,
        },
        timeout=60,
    ).json()

    if not finish_res.get("success"):
        raise RuntimeError(f"Gagal publish Reels FB: {finish_res}")

    return video_id


def main():
    drive = get_drive_service()
    video = get_next_video(drive)

    if not video:
        print("Antrean kosong. Tidak ada video baru di FB_Reels_Queue.")
        return

    local_file = f"/tmp/{video['name']}"
    print(f"Memproses video: {video['name']}")

    download_video(drive, video["id"], local_file)
    caption = generate_viral_caption(video["name"])
    print(f"Caption Claude:\n{caption}\n")

    fb_video_id = upload_facebook_reel(local_file, caption)
    print(f"Sukses tayang di Fanpage! Video ID: {fb_video_id}")

    move_to_done(drive, video["id"])
    os.remove(local_file)
    print("File dipindahkan ke FB_Reels_Published.")


if __name__ == "__main__":
    main()
