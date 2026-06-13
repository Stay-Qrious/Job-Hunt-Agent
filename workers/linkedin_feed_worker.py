import asyncio
import re
import urllib.parse
from playwright.async_api import BrowserContext
import database

class LinkedInFeedWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def scan_social_feed(self, company_keyword: str):
        """Scrapes the LinkedIn network stream looking for active hiring links posted for specific companies."""
        self.page = await self.context.new_page()
        
        # Human search footprint targeting real human recruiters posting open portal links
        query_string = f'{company_keyword} "hiring" AND ("link" OR "form" OR "apply")'
        encoded_query = urllib.parse.quote(query_string)
        feed_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&origin=SWITCH_SEARCH_VERTICAL"
        
        print(f"\n[LINKEDIN SOCIAL] Sweeping network logs for: '{company_keyword.upper()}'")
        try:
            await self.page.goto(feed_url, wait_until="load", timeout=35000)
            await asyncio.sleep(5)

            # Scroll layout down to unpack dynamic lazy-loaded tracking targets
            for step in range(3):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight * 1.2);")
                await asyncio.sleep(1.5)

            raw_page_source = await self.page.content()
            
            # Extract application portals, external tracking forms, or career vectors embedded anywhere inside the data string
            raw_links = re.findall(r'(https?://[^\s<>"]+|www\.[^\s<>"]+)', raw_page_source)
            
            staged_count = 0
            for link in raw_links:
                clean_url = link.split('?')[0].rstrip('.,;)("}\\')
                clean_lower = clean_url.lower()
                
                # Track application systems
                if any(k in clean_lower for k in ["forms.gle", "docs.google.com/forms", "typeform", "zoho", "unstop", "careers", "job"]):
                    if not any(noise in clean_lower for noise in ["linkedin.com/feed", "static", "sharing", "api"]):
                        
                        # Evaluate mass hiring content markers around context layout segments
                        is_mass = 1 if any(m in raw_page_source.lower() for m in ["mass", "mega", "drive", "off-campus", "batch", "hiring bulk"]) else 0
                        
                        success = database.enqueue_portal(company_keyword, "LinkedIn_Social_Mine", clean_url, is_mass, f"Extracted from {company_keyword} sweep grid.")
                        if success:
                            staged_count += 1
                            print(f"   | -> Harvested Application Path: {clean_url[:65]}... (Mass Drive: {is_mass})")

            print(f" -> Completed company channel tracking loop. Staged {staged_count} new links.")

        except Exception as e:
            print(f"[LINKEDIN ERROR] Channel sweep bypassed: {e}")
        finally:
            await self.page.close()