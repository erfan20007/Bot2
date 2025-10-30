import requests
import json
import os 
import sys
import time

# === تنظیمات ===
API_KEY = os.environ.get('LINKO_API_KEY') 
if not API_KEY:
    print("❌ خطا: کلید API (LINKO_API_KEY) در GitHub Secrets تنظیم نشده است.")
    sys.exit(1)

API_URL = "https://linko.me/api/url/add"

# تنظیمات محدودیت (Rate Limit)
REQUESTS_PER_BATCH = 5
SLEEP_BETWEEN_BATCHES = 60 

INPUT_FILE = "sso_links.txt"
OUTPUT_FILE = "final_shortened_links.txt"
FAILED_LINKS_OUTPUT_FILE = "failed_links_to_retry.txt"

HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# === تابع کوتاه کننده ===
def shorten_link_linko(long_url):
    payload = {"url": long_url}
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("error") == 0 and data.get("shorturl"):
                    short_url = data['shorturl'].replace(r'\/', '/')
                    return short_url
                else:
                    print(f"  [!] خطای API: {data.get('message', 'پاسخ نامعتبر')}")
                    return None
            except json.JSONDecodeError:
                print(f"  [!] خطا: پاسخ سرور JSON معتبر نبود: {response.text}")
                return None
        else:
            if response.status_code == 429:
                print(f"  [!] خطای 429: محدودیت Rate Limit فعال شد.")
            else:
                print(f"  [!] خطای HTTP: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"  [!] خطای شبکه: {e}")
        return None

# === تابع اصلی ===
def main():
    print("=" * 40)
    print("🚀 اسکریپت کوتاه کننده (در حال اجرا روی GitHub Actions) 🚀")
    print(f"خواندن از: {INPUT_FILE}")
    print("=" * 40)

    links_to_process = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        current_phone = None
        for line in lines:
            line = line.strip()
            if line.startswith("Phone:"):
                current_phone = line.split("Phone:", 1)[1].strip()
            elif line.startswith("Link:") and current_phone:
                long_link = line.split("Link:", 1)[1].strip()
                links_to_process.append({"phone": current_phone, "long_link": long_link})
                current_phone = None
    except Exception as e:
        print(f"❌ خطا در خواندن فایل '{INPUT_FILE}': {e}")
        sys.exit(1)

    if not links_to_process:
        print("⚠️ هیچ لینکی برای پردازش در فایل ورودی یافت نشد.")
        sys.exit()

    print(f"✅ {len(links_to_process)} لینک برای پردازش یافت شد.")

    successful_links = []
    failed_links = []
    request_count = 0 
    total_links = len(links_to_process)

    for i, item in enumerate(links_to_process):
        phone = item['phone']
        long_link = item['long_link']

        print(f"\n📞 [{i+1}/{total_links}] در حال پردازش لینک برای: {phone}")

        if request_count > 0 and request_count % REQUESTS_PER_BATCH == 0:
            print("-" * 30)
            print(f"(!) به سقف دسته ({REQUESTS_PER_BATCH} درخواست) رسیدیم.")
            print(f"⏳ در حال انتظار به مدت {SLEEP_BETWEEN_BATCHES} ثانیه...")
            time.sleep(SLEEP_BETWEEN_BATCHES)
            print("⏳ انتظار تمام شد. ادامه می‌دهیم...")
            print("-" * 30)

        short_url = shorten_link_linko(long_link)
        request_count += 1

        if short_url:
            print(f"  [✔] موفقیت: {short_url}")
            successful_links.append({"phone": phone, "short_link": short_url})
        else:
            print(f"  [✖] ناموفق. لینک در فایل خطا ذخیره می‌شود.")
            failed_links.append(item)
            if 'response' in locals() and hasattr(response, 'status_code') and response.status_code == 429:
                 print(f"(!) خطای 429 دریافت شد. {SLEEP_BETWEEN_BATCHES} ثانیه صبر می‌کنیم...")
                 time.sleep(SLEEP_BETWEEN_BATCHES)

    print("\n" + "=" * 40)
    print("🏁 عملیات تمام شد. در حال ذخیره نتایج...")

    if successful_links:
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                for item in successful_links:
                    f.write(f"Phone: {item['phone']}\n")
                    f.write(f"Short Link: {item['short_link']}\n")
                    f.write("-" * 30 + "\n")
            print(f"🎉 {len(successful_links)} لینک موفق در '{OUTPUT_FILE}' ذخیره شد.")
        except IOError as e:
            print(f"❌ خطا در ذخیره‌سازی فایل موفق: {e}")
    else:
        print("😔 هیچ لینکی با موفقیت کوتاه نشد.")

    if failed_links:
        try:
            with open(FAILED_LINKS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
                for item in failed_links:
                    f.write(f"Phone: {item['phone']}\n")
                    f.write(f"Link: {item['long_link']}\n")
                    f.write("-" * 30 + "\n")
            print(f"⚠️ {len(failed_links)} لینک ناموفق در '{FAILED_LINKS_OUTPUT_FILE}' ذخیره شد.")
        except IOError as e:
            print(f"❌ خطا در ذخیره‌سازی فایل ناموفق: {e}")
    else:
        print("✅ تمام لینک‌ها با موفقیت پردازش شدند (هیچ خطایی وجود نداشت).")

    print("=" * 40)

if __name__ == "__main__":
    main()
