import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import feedparser

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def find_rss_feeds(url):
    feeds = set()
    try:
        response = requests.get(url, timeout=10, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Search for <link> tags in <head>
        for link in soup.find_all('link', rel=True):
            if 'alternate' in link['rel']:
                if link.get('type') in ['application/rss+xml', 'application/atom+xml', 'text/xml']:
                    href = link.get('href')
                    if href:
                        feeds.add(urljoin(url, href))

        # 2. Search for <a> tags that might contain "rss" or "feed" in href
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Basic filter to avoid obvious non-feed links, but still need verification
            if 'rss' in href.lower() or 'feed' in href.lower() or 'xml' in href.lower():
                 full_url = urljoin(url, href)
                 if full_url.endswith('.xml') or '/rss' in full_url or '/feed' in full_url:
                     feeds.add(full_url)

    except Exception as e:
        print(f"Error accessing {url}: {e}")

    # 3. Try common suffixes
    common_suffixes = ['/rss', '/feed', '/rss.xml', '/feed.xml']
    for suffix in common_suffixes:
        try_url = urljoin(url, suffix)
        if try_url not in feeds:
            try:
                resp = requests.head(try_url, timeout=5, allow_redirects=True, headers=HEADERS)
                if resp.status_code == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    if 'xml' in content_type or 'rss' in content_type:
                        feeds.add(try_url)
            except:
                pass

    return list(feeds)

def analyze_feed(feed_url):
    try:
        # Use a custom user agent for the feed fetching as well
        response = requests.get(feed_url, timeout=10, headers=HEADERS)

        # Check Content-Type to avoid parsing HTML pages as feeds
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' in content_type:
             return {
                'url': feed_url,
                'error': 'Content-Type indicates HTML, not a valid feed.'
            }

        d = feedparser.parse(response.content)

        if d.bozo and not d.entries:
             return {
                'url': feed_url,
                'error': 'Feedparser failed to parse content or no entries found.'
            }

        return {
            'url': feed_url,
            'title': d.feed.get('title', 'No Title'),
            'description': d.feed.get('description', 'No Description'),
            'items_count': len(d.entries)
        }
    except Exception as e:
        return {
            'url': feed_url,
            'error': str(e)
        }

def main():
    websites = [
        "https://www.folha.uol.com.br",
        "https://www.estadao.com.br",
        "https://oglobo.globo.com",
        "https://g1.globo.com",
        "https://gauchazh.clicrbs.com.br",
        "https://www.correiobraziliense.com.br",
        "https://www.em.com.br",
        "https://www.gazetadopovo.com.br",
        "https://www.jb.com.br",
        "https://www.uol.com.br",
        "https://www.brasildefato.com.br",
        "https://www.agazeta.com.br"
    ]

    results = {}

    for site in websites:
        print(f"Scanning {site}...")
        feed_urls = find_rss_feeds(site)

        valid_feeds = []

        if feed_urls:
            print(f"Found {len(feed_urls)} potential feeds for {site}. Analyzing...")
            for url in feed_urls:
                feed_info = analyze_feed(url)
                if 'error' not in feed_info:
                    valid_feeds.append(feed_info)
                else:
                    print(f"Skipping invalid feed {url}: {feed_info['error']}")
        else:
            print(f"No feeds found for {site}")

        if valid_feeds:
            results[site] = {'feeds': valid_feeds}
        else:
             results[site] = {'feeds': [], 'note': 'No valid feeds found'}

    with open('rss_feeds.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("Done. Results saved to rss_feeds.json")

if __name__ == "__main__":
    main()
