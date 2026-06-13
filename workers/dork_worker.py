import asyncio
import urllib.parse
from playwright.async_api import BrowserContext
import database
import config

class DorkWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def check_company_openings(self, company_name: str):
        """Hunts for the official corporate career portal page, regardless of what software platform they host it on."""
        self.page = await self.context.new_page()
        
        # UPGRADE: Broaden the dork query to find ANY official career portal page 
        # while explicitly blocking aggregate job boards like LinkedIn and Indeed
        raw_query = f'"{config.SEARCH_KEYWORD}" site:*.com/careers OR site:*.com/jobs "{company_name}" -site:linkedin.com -site:indeed.com -site:naukri.com'
        encoded_query = urllib.parse.quote(raw_query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        print(f"[DORK WORKER] Hunting official corporate portals for: {company_name.upper()}...")
        try:
            await self.page.goto(search_url, wait_until="load")
            await asyncio.sleep(4) 
            
            # Extract links from main Google search result containers
            search_anchors = await self.page.query_selector_all("div.g a[data-ved], a:has(h3)")
            discovered_urls = []
            
            for anchor in search_anchors:
                href = await anchor.get_attribute("href")
                if href and href.startswith("http") and not any(x in href for x in ["google.com", "linkedin", "naukri", "indeed"]):
                    if href not in discovered_urls:
                        discovered_urls.append(href)
            
            print(f" -> Found {len(discovered_urls)} potential official company portal links.")
            
            for portal_url in discovered_urls[:2]:
                # Generate tracking hash from unique parts of the URL string path
                url_hash = portal_url.replace("https://", "").replace("http://", "").split("/")[0] + "-jobs"
                
                if database.is_job_processed(url_hash):
                    continue
                    
                print(f" -> Enqueueing verified official portal target: {portal_url[:70]}...")
                database.enqueue_portal(company_name, "Official_Corporate_Portal", portal_url)
                database.log_job(url_hash, company_name, "STAGED_PORTAL_ONLY")
                
        except Exception as e:
            print(f"[DORK ERROR] Failed corporate scan for {company_name}: {e}")
        finally:
            await self.page.close()