"""
============================================================
  JECRC Foundation - College Helpdesk AI Chatbot
  Web Scraper - Auto-read college website for latest info
============================================================
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime


class WebScraper:
    """Scrapes JECRC Foundation website for latest information"""

    def __init__(self):
        self.base_url = "https://jecrcfoundation.com"
        self.headers = {
            'User-Agent': 'JECRC-Chatbot-Scraper/1.0 (Educational Project)'
        }
        self.scraped_data = {}
        print("✅ WebScraper initialized")

    def _fetch_page(self, url):
        """Fetch a webpage and return BeautifulSoup object"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            print(f"⚠️ Error fetching {url}: {e}")
            return None

    def _clean_text(self, text):
        """Clean extracted text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def scrape_homepage(self):
        """Scrape main homepage"""
        print("🔄 Scraping homepage...")
        soup = self._fetch_page(self.base_url)
        if not soup:
            return {}

        data = {
            'title': '',
            'highlights': [],
            'announcements': [],
            'stats': []
        }

        # Get title
        title_tag = soup.find('title')
        if title_tag:
            data['title'] = self._clean_text(title_tag.text)

        # Get all headings for highlights
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text = self._clean_text(heading.text)
            if text and len(text) > 5:
                data['highlights'].append(text)

        # Get paragraphs
        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 20:
                data['announcements'].append(text)

        self.scraped_data['homepage'] = data
        print(f"✅ Homepage scraped: {len(data['highlights'])} highlights found")
        return data

    def scrape_about(self):
        """Scrape About Us page"""
        print("🔄 Scraping about page...")
        soup = self._fetch_page(f"{self.base_url}/about-us")
        if not soup:
            return {}

        data = {
            'content': [],
            'stats': []
        }

        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 20:
                data['content'].append(text)

        self.scraped_data['about'] = data
        print(f"✅ About page scraped: {len(data['content'])} paragraphs")
        return data

    def scrape_departments(self):
        """Scrape Departments page"""
        print("🔄 Scraping departments page...")
        soup = self._fetch_page(f"{self.base_url}/department")
        if not soup:
            return {}

        data = {
            'departments': [],
            'details': []
        }

        for heading in soup.find_all(['h2', 'h3', 'h4']):
            text = self._clean_text(heading.text)
            if text and len(text) > 3:
                data['departments'].append(text)

        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 20:
                data['details'].append(text)

        self.scraped_data['departments'] = data
        print(f"✅ Departments page scraped: {len(data['departments'])} departments")
        return data

    def scrape_placement(self):
        """Scrape Placement page"""
        print("🔄 Scraping placement page...")
        soup = self._fetch_page(f"{self.base_url}/placement")
        if not soup:
            return {}

        data = {
            'highlights': [],
            'companies': [],
            'stats': []
        }

        for heading in soup.find_all(['h2', 'h3']):
            text = self._clean_text(heading.text)
            if text:
                data['highlights'].append(text)

        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 10:
                data['stats'].append(text)

        # Try to find company names from images alt text or list items
        for img in soup.find_all('img', alt=True):
            alt = self._clean_text(img['alt'])
            if alt and len(alt) > 2:
                data['companies'].append(alt)

        self.scraped_data['placement'] = data
        print(f"✅ Placement page scraped")
        return data

    def scrape_admission(self):
        """Scrape Admission page"""
        print("🔄 Scraping admission page...")
        soup = self._fetch_page(f"{self.base_url}/admission")
        if not soup:
            return {}

        data = {
            'info': [],
            'steps': [],
            'dates': []
        }

        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 15:
                data['info'].append(text)

        for li in soup.find_all('li'):
            text = self._clean_text(li.text)
            if text and len(text) > 5:
                data['steps'].append(text)

        self.scraped_data['admission'] = data
        print(f"✅ Admission page scraped")
        return data

    def scrape_contact(self):
        """Scrape Contact page"""
        print("🔄 Scraping contact page...")
        soup = self._fetch_page(f"{self.base_url}/contact-us")
        if not soup:
            return {}

        data = {
            'address': [],
            'phone': [],
            'email': [],
            'other': []
        }

        page_text = soup.get_text()

        # Find phone numbers
        phones = re.findall(r'[\+]?[\d\-\(\)\s]{10,}', page_text)
        data['phone'] = [p.strip() for p in phones if len(p.strip()) > 8]

        # Find emails
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
        data['email'] = list(set(emails))

        for p in soup.find_all('p'):
            text = self._clean_text(p.text)
            if text and len(text) > 10:
                data['other'].append(text)

        self.scraped_data['contact'] = data
        print(f"✅ Contact page scraped: {len(data['email'])} emails, {len(data['phone'])} phones")
        return data

    def scrape_all(self):
        """Scrape all pages and return combined data"""
        print("\n" + "=" * 50)
        print("🌐 Starting Full Website Scrape...")
        print("=" * 50)

        self.scrape_homepage()
        self.scrape_about()
        self.scrape_departments()
        self.scrape_placement()
        self.scrape_admission()
        self.scrape_contact()

        # Save to JSON
        self.scraped_data['last_updated'] = datetime.now().isoformat()
        try:
            with open('scraped_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.scraped_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ All data saved to scraped_data.json")
        except Exception as e:
            print(f"⚠️ Error saving: {e}")

        print("=" * 50)
        print("🌐 Scraping Complete!")
        print("=" * 50 + "\n")

        return self.scraped_data

    def get_scraped_data(self):
        """Return all scraped data"""
        return self.scraped_data


# Testing
if __name__ == "__main__":
    scraper = WebScraper()
    data = scraper.scrape_all()
    print(f"\n📊 Total sections scraped: {len(data)}")
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"  📁 {key}: {len(value)} sub-sections")
        else:
            print(f"  📄 {key}: {value}")
