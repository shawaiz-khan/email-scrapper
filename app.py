from flask import Flask, render_template, request, redirect, url_for
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urldefrag

app = Flask(__name__)

USERNAME = "admin"
PASSWORD = "trial$123"

logged_in = False


def ensure_scheme(url):
    if not urlparse(url).scheme:
        return "http://" + url
    return url


def is_valid_email(email):
    return (
        re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$", email)
        is not None
    )


async def fetch(session, url):
    try:
        async with session.get(url, timeout=60) as response:
            if "text/html" in response.headers.get("Content-Type", ""):
                return await response.text()
            else:
                return None
    except Exception as e:
        return None


def normalize_url(base, link):
    full_url = urljoin(base, link)
    full_url, _ = urldefrag(full_url)
    return full_url


async def scrape_emails(url, session, visited=None):
    if visited is None:
        visited = set()

    emails = set()
    url = ensure_scheme(url)

    if url in visited:
        return emails
    visited.add(url)

    html_content = await fetch(session, url)
    if not html_content:
        return emails

    soup = BeautifulSoup(html_content, "html.parser")

    potential_emails = re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", soup.text
    )
    for email in potential_emails:
        if is_valid_email(email):
            emails.add(email)

    tasks = []
    for link in soup.find_all("a", href=True):
        full_url = normalize_url(url, link["href"])
        if urlparse(full_url).netloc == urlparse(url).netloc:
            tasks.append(scrape_emails(full_url, session, visited))

    results = await asyncio.gather(*tasks)
    for result in results:
        emails.update(result)

    return emails


@app.route("/login", methods=["GET", "POST"])
def login():
    global logged_in
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == USERNAME and password == PASSWORD:
            logged_in = True
            return redirect(url_for("index"))
        else:
            return "Invalid credentials, please try again."

    return render_template("index.html", logged_in=logged_in)


@app.route("/logout", methods=["POST"])
def logout():
    global logged_in
    logged_in = False
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
async def index():
    if not logged_in:
        return redirect(url_for("login"))

    emails = []
    if request.method == "POST":
        url = request.form["url"]
        async with aiohttp.ClientSession() as session:
            emails = await scrape_emails(url, session)
    return render_template("index.html", emails=emails, logged_in=logged_in)


if __name__ == "__main__":
    app.run(debug=True)
