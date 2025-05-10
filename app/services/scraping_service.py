import requests
from bs4 import BeautifulSoup
import time
import random
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

class ScrapingService:
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        """
        Initialize the scraping service with configurable timeout and retry settings.
        
        Args:
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _get_random_user_agent(self) -> str:
        """Return a random user agent from the list."""
        return random.choice(self.user_agents)

    def _is_valid_url(self, url: str) -> bool:
        """Validate if the provided URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def scrape_page(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Scrape a web page and return its content and metadata.
        
        Args:
            url (str): The URL to scrape
            headers (Optional[Dict[str, str]]): Additional headers to include in the request
            
        Returns:
            Dict[str, Any]: Dictionary containing the scraped data and metadata
        """
        if not self._is_valid_url(url):
            raise ValueError("Invalid URL provided")

        # Prepare headers
        default_headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        if headers:
            default_headers.update(headers)

        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=default_headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parse the HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract basic metadata
                title = soup.title.string if soup.title else None
                meta_description = soup.find('meta', attrs={'name': 'description'})
                description = meta_description['content'] if meta_description else None
                main_content = soup.select_one(".field--name-body")
                main_content_text = main_content.get_text(strip=True) if main_content else None
                # Add a small delay to be respectful to the server
                time.sleep(random.uniform(1, 3))
                
                return {
                    'url': url,
                    'status_code': response.status_code,
                    'title': title,
                    'description': description,
                    'content': response.text,
                    'parsed_html': soup,
                    'headers': dict(response.headers),
                    'main_content': main_content_text
                }
                
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to scrape {url} after {self.max_retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def extract_links(self, url: str) -> list:
        """
        Extract all links from a webpage.
        
        Args:
            url (str): The URL to scrape for links
            
        Returns:
            list: List of extracted links
        """
        result = self.scrape_page(url)
        soup = result['parsed_html']
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Convert relative URLs to absolute URLs
            if not href.startswith(('http://', 'https://')):
                href = requests.compat.urljoin(url, href)
            links.append(href)
            
        return links

    def extract_text(self, url: str, selector: Optional[str] = None) -> str:
        """
        Extract text content from a webpage, optionally filtered by a CSS selector.
        
        Args:
            url (str): The URL to scrape
            selector (Optional[str]): CSS selector to filter content
            
        Returns:
            str: Extracted text content
        """
        result = self.scrape_page(url)
        soup = result['parsed_html']
        
        if selector:
            elements = soup.select(selector)
            text = ' '.join([elem.get_text(strip=True) for elem in elements])
        else:
            text = soup.get_text(strip=True)
            
        return text
