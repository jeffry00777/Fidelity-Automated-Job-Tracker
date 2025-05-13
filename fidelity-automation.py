from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.message import EmailMessage
import smtplib
import os
import time

# ---------------- CONFIG ----------------
SEARCH_URL = "https://jobs.fidelity.com/en/jobs/?location=Massachusetts,%20USA&search=software"
SEEN_JOBS_FILE = "seen_jobs_fidelity.txt"
EMAIL_SENDER = "stiffler00777@gmail.com"
EMAIL_PASSWORD = "********************"  
EMAIL_RECEIVER = "jeffrylivingston5@gmail.com"
# ----------------------------------------

def load_seen_jobs():
    seen = {}
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|||")
                if len(parts) == 3:
                    title, url, status = parts
                elif len(parts) == 2:
                    title, url = parts
                    status = "Pending"
                else:
                    continue
                seen[title] = (url, status)
    return seen

def save_seen_jobs(jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        for title, (url, status) in jobs.items():
            f.write(f"{title}|||{url}|||{status}\n")

def send_email_notification(jobs):
    msg = EmailMessage()
    msg["Subject"] = "Fidelity Jobs - Posted in Last 7 Days"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    body = "New Fidelity jobs posted within the last 7 days:\n\n"
    for title, url in jobs.items():
        job_id = url.split("/")[-2] if "/jobs/" in url else "N/A"
        body += f"- {title}\n  Job ID: {job_id}\n  URL: {url}\n\n"

    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def fetch_recent_jobs():
    recent_jobs = {}
    cutoff = datetime.now() - timedelta(days=7)
    base_url = "https://jobs.fidelity.com/en/jobs/?page={page}&search=software&location=Massachusetts,%20USA&pagesize=20&origin=filtered#results"

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(base_url.format(page=1))
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Detect max page from pagination
    pagination = soup.select("ul.pagination li.page-item a.page-link")
    page_numbers = [int(link.text) for link in pagination if link.text.isdigit()]
    max_pages = max(page_numbers) if page_numbers else 1
    print(f"📄 Found {max_pages} pages of results")

    for page in range(1, max_pages + 1):
        print(f"🔍 Scraping page {page}...")
        driver.get(base_url.format(page=page))
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        job_cards = soup.find_all("div", class_="card card-job")

        for card in job_cards:
            try:
                title_elem = card.find("h2", class_="card-title").find("a")
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                url = "https://jobs.fidelity.com" + title_elem['href']

                location_elem = card.select_one("li.list-inline-item > div")
                location = location_elem.text.strip() if location_elem else "N/A"

                date_span = card.find("span", string=lambda s: s and "Posted" in s)
                if not date_span:
                    continue
                date_str = date_span.text.replace("Posted", "").strip()
                post_date = datetime.strptime(date_str, "%b %d").replace(year=datetime.now().year)

                if post_date >= cutoff:
                    key = f"{title} | {location}"
                    recent_jobs[key] = url
            except Exception as e:
                print("Error parsing job card:", e)

    driver.quit()
    return recent_jobs

def main():
    recent_jobs = fetch_recent_jobs()
    seen_jobs = load_seen_jobs()
    changes = {}

    for title, url in recent_jobs.items():
        if title not in seen_jobs or seen_jobs[title][1] not in ["applied", "Notified"]:
            changes[title] = url

    if changes:
        print(f"📬 Sending {len(changes)} new job(s)...")
        send_email_notification(changes)

        # Mark newly notified jobs
        for title, url in changes.items():
            seen_jobs[title] = (url, "Notified")

        # Preserve existing jobs not in recent fetch
        for title, (url, status) in recent_jobs.items():
            if title not in seen_jobs:
                seen_jobs[title] = (url, status)

        save_seen_jobs(seen_jobs)
    else:
        print("No new Fidelity jobs found in the last 7 days.")

def send_email_notification(jobs):
    msg = EmailMessage()
    msg["Subject"] = "🆕 Fidelity Jobs - Posted in Last 7 Days"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    body = "New Fidelity jobs posted within the last 7 days:\n\n"
    for title, url in jobs.items():
        job_id = url.split("/")[-2] if "/jobs/" in url else "N/A"
        body += f"- {title}\n  Job ID: {job_id}\n  URL: {url}\n\n"

    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)


if __name__ == "__main__":
    main()
