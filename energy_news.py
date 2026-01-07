
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SITES = [
    "https://www.energypress.gr/",
    "https://www.naftemporiki.gr/energy/",
    "https://www.ot.gr/category/energeia/",
]

KEYWORDS = ["ενέργ", "ΑΠΕ", "ηλεκτρ", "φωτοβολ", "μπαταρ", "BESS", "PV", "YPEN"]

EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")


def scrape_site(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []

        for a in soup.find_all("a"):
            title = a.get_text(strip=True)
            link = a.get("href")

            if not title or not link:
                continue

            if link.startswith("/"):
                link = url.rstrip("/") + link

            results.append((title, link))

        return results
    except:
        return []


def filter_energy(news):
    return [
        (title, link)
        for title, link in news
        if any(k.lower() in title.lower() for k in KEYWORDS)
    ]


def create_report(data):
    text = "🔋 DAILY ENERGY NEWS REPORT\n\n"
    for site, items in data.items():
        text += f"=== {site} ===\n"
        if not items:
            text += "• Δεν βρέθηκαν νέα.\n\n"
        else:
            for title, link in items:
                text += f"• {title}\n  {link}\n\n"
    return text


def send_email(body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USERNAME
    msg["To"] = EMAIL_RECIPIENT
    msg["Subject"] = "Daily Energy News Report"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_USERNAME, EMAIL_RECIPIENT, msg.as_string())
    server.quit()


def main():
    results = {}
    for site in SITES:
        raw = scrape_site(site)
        filt = filter_energy(raw)
        results[site] = filt

    report = create_report(results)
    send_email(report)


if __name__ == "__main__":
    main()
