def scrape_emails(url, visited=None):
    if visited is None:
        visited = set()
        
    emails = set()
    if url in visited:
        return emails
    visited.add(url)
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract emails from the page
            emails.update(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', soup.text))
            
            # Follow links on the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Join the relative link with the base URL
                full_url = urljoin(url, href)
                # Check if the link is within the same domain to avoid external links
                if urlparse(full_url).netloc == urlparse(url).netloc:
                    emails.update(scrape_emails(full_url, visited))
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    
    return emails