from flask import Flask, render_template, request
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urldefrag

app = Flask(__name__)

def ensure_scheme(url):
    """Ensure the URL has a scheme, defaulting to http:// if missing."""
    if not urlparse(url).scheme:
        return 'http://' + url
    return url

def is_valid_email(email):
    """Checks if the email has a valid structure."""
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$", email) is not None

async def fetch(session, url):
    """Fetch the content of the URL."""
    try:
        async with session.get(url, timeout=60) as response:
            if 'text/html' in response.headers.get('Content-Type', ''):
                return await response.text()
            else:
                print(f"Skipping non-HTML content at {url}")
                return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def normalize_url(base, link):
    """Normalize and defrag URLs to ensure consistency."""
    full_url = urljoin(base, link)
    full_url, _ = urldefrag(full_url)  # Remove fragment identifiers
    return full_url

async def scrape_emails(url, session, visited=None):
    if visited is None:
        visited = set()
        
    emails = set()
    url = ensure_scheme(url)  # Ensure the URL has a scheme
    
    if url in visited:
        return emails
    visited.add(url)
    
    html_content = await fetch(session, url)
    if not html_content:
        return emails
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract potential emails from the page
    potential_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', soup.text)
    for email in potential_emails:
        if is_valid_email(email):
            emails.add(email)
    
    # Follow links on the page
    tasks = []
    for link in soup.find_all('a', href=True):
        full_url = normalize_url(url, link['href'])

        # Follow links within the same domain
        if urlparse(full_url).netloc == urlparse(url).netloc:
            tasks.append(scrape_emails(full_url, session, visited))

    results = await asyncio.gather(*tasks)
    for result in results:
        emails.update(result)
    
    return emails

@app.route('/', methods=['GET', 'POST'])
async def index():
    emails = []
    if request.method == 'POST':
        url = request.form['url']
        async with aiohttp.ClientSession() as session:
            emails = await scrape_emails(url, session)
    return render_template('index.html', emails=emails)

if __name__ == '__main__':
    app.run(debug=True)
