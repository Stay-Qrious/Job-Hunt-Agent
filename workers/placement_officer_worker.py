import asyncio
import re
from playwright.async_api import BrowserContext
import database

class PlacementOfficerWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def scrape_latest_drives(self):
        """Scrapes the placement officer aggregation hub for off-campus drive vectors."""
        print(f"\n[PLACEMENT HUB] Connecting to job aggregator index...")
        self.page = await self.context.new_page()
        
        try:
            await self.page.goto("https://www.placement-officer.com/", wait_until="load", timeout=30000)
            await asyncio.sleep(4)

            # Target the latest post card links populated on the aggregation board
            job_links = await self.page.query_selector_all("a[href*='placement-officer.com/']")
            print(f" -> Found {len(job_links)} recent vacancy footprints on layout canvas.")

            staged_count = 0
            evaluated_urls = set()

            for link in job_links[:30]: # Expand window to evaluate top 30 links
                url = await link.get_attribute("href")
                if not url or url in evaluated_urls:
                    continue
                
                url_lower = url.lower()
                
                # --- NOISE FILTER SHIELD ---
                # Drop structural layout pages, feed syndications, labels, and disclaimer fragments
                if any(noise in url_lower for noise in [
                    "/p/terms", "/p/privacy", "/p/disclaimer", "/p/about", "/p/contact",
                    "search/label/", "feeds/posts/default", "search?updated-max"
                ]):
                    continue
                
                evaluated_urls.add(url)
                link_text = (await link.inner_text()).strip()
                
                if len(link_text) < 15: # Skip short tracking text nodes or blank graphic arrows
                    continue

                # Signature markers indicating mass volume drives or tier-1 enterprise sweeps
                link_lower = link_text.lower()
                is_mass = 1 if any(m in link_lower for m in ["mass", "mega", "drive", "off campus", "hiring", "freshers", "2025", "2026"]) else 0
                
                # Isolate company name context out of description string text
                company_match = re.search(r"([A-Za-z0-9\s.]+)\s+(?:Recruitment|Off|Mega|Drive|Hiring)", link_text, re.IGNORECASE)
                company = company_match.group(1).strip() if company_match else "Enterprise Off-Campus"

                # Save the tracking index link straight to the repository database queue
                success = database.enqueue_portal(company, "Placement_Officer_Hub", url, is_mass, link_text)
                if success:
                    staged_count += 1
                    status_flag = "[MASS DRIVE DETECTED]" if is_mass else "[DIRECT VACANCY]"
                    print(f"   | -> Staged: {company.upper()} {status_flag} -> {url[:50]}...")

            print(f" -> Aggregator processing run complete. Ingested {staged_count} clean operational targets.")

        except Exception as e:
            print(f"[PLACEMENT HUB ERROR] Pipeline failed: {e}")
        finally:
            await self.page.close()