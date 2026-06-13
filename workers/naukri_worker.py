import asyncio
import re
from playwright.async_api import BrowserContext
import config
import database

class NaukriWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    def _extract_job_id(self, url: str) -> str:
        if not url: return ""
        match = re.search(r"jdId=(\d+)", url)
        if match: return match.group(1)
        slug_match = re.search(r"-(\d+)(?:\?|$)", url)
        return slug_match.group(1) if slug_match else url

    def _parse_experience(self, exp_text: str) -> int:
        """Helper to extract the maximum required experience year from text like '2-5 Yrs' or '3 Yrs'."""
        if not exp_text: return 0
        nums = [int(s) for s in re.findall(r'\d+', exp_text)]
        return nums[0] if nums else 0

    async def run_sweep(self):
        self.page = await self.context.new_page()
        
        for technical_query in config.NAUKRI_KEYWORDS:
            print(f"\n[NAUKRI WORKER] Launching sweep for specialization: '{technical_query}'")
            try:
                # Add freshness filters directly to the URL query string structure
                # 'freshDays=7' forces Naukri to only return jobs posted in the last 7 days
                encoded_query = technical_query.replace(" ", "-")
                fresh_url = f"https://www.naukri.com/{encoded_query}-jobs?freshDays=7"
                
                await self.page.goto(fresh_url, wait_until="load")
                await asyncio.sleep(3)

                job_cards = await self.page.query_selector_all("div.cust-job-tuple, article.jobTuple")
                print(f"[NAUKRI WORKER] Detected {len(job_cards)} recent listings matching profile on Page 1.")

                ALLOWED_TECH_MARKERS = ["engineer", "developer", "programmer", "sde", "tech", "architect", "integration", "cpi", "backend"]

                for index, card in enumerate(job_cards[:10]):
                    try:
                        title_link = await card.query_selector("a.title")
                        if not title_link: continue

                        raw_url = await title_link.get_attribute("href")
                        job_id = self._extract_job_id(raw_url)
                        
                        title_text = (await title_link.inner_text()).lower()
                        company_element = await card.query_selector("a.comp-name, a.companyName")
                        company_name = (await company_element.inner_text()).strip().lower() if company_element else "unknown"

                        print(f"\n   [EVALUATING CARD {index + 1}] {company_name.upper()} -> {title_text.upper()}")

                        # 1. CRITICAL GUARD: Experience Check Matrix
                        # Pull the experience node value string straight out of the active card template block
                        exp_element = await card.query_selector("span.expwdth, span.exp, li.experience span")
                        if exp_element:
                            exp_text = (await exp_element.inner_text()).strip()
                            required_exp = self._parse_experience(exp_text)
                            user_max_exp = int(config.PROFILE_ANSWERS["experience"])
                            
                            print(f"   | Required Exp: {exp_text} | Profile Bound: {user_max_exp} Years")
                            if required_exp > (user_max_exp + 2): # Allows safety buffer up to matching tiers
                                print(f"   | -> [FILTERED] EXPERIENCE MISMATCH. Job requires senior tier ({exp_text}). Skipping...")
                                continue

                        # 2. Tech Title Guard Match
                        if not any(marker in title_text for marker in ALLOWED_TECH_MARKERS):
                            print("   | -> [FILTERED] Non-technical title block string. Skipping...")
                            continue

                        # 3. Business Noise Filter Guard
                        if any(bad_word in title_text for bad_word in ["finance", "analyst", "risk", "credit", "operations", "recruiter", "finops", "ui/ux", "designer"]):
                            print("   | -> [FILTERED] Core role matches non-tech business descriptors. Skipping...")
                            continue

                        if database.is_job_processed(job_id):
                            print(f"   | -> [MEMORY HIT] Job ID already processed historically. Skipping...")
                            continue

                        if any(blocked in company_name for blocked in config.BLOCKLIST_COMPANIES):
                            print(f"   | -> [FILTERED] Matches blocklist profiles. Skipping...")
                            database.log_job(job_id, company_name, "SKIPPED_BLOCKLIST")
                            continue

                        print(f"   | -> [PROCEED] Aligned match found. Opening application context...")
                        async with self.context.expect_page() as new_page_info:
                            await title_link.click(force=True)
                        
                        job_page = await new_page_info.value
                        await job_page.bring_to_front()
                        await asyncio.sleep(3)

                        apply_button = await job_page.wait_for_selector(
                            "button.apply-button, button:has-text('Apply'), button:has-text('Apply on company site')", 
                            timeout=5000
                        )
                        button_text = (await apply_button.inner_text()).strip()

                        if "company site" in button_text.lower():
                            print("   | -> [REDIRECT] Intercepting corporate site tracking gateway link...")
                            async with self.context.expect_page() as portal_page_info:
                                await apply_button.click(force=True)
                            
                            portal_page = await portal_page_info.value
                            await portal_page.bring_to_front()
                            await asyncio.sleep(4) 
                            
                            external_company_url = portal_page.url
                            database.enqueue_portal(company_name, "Naukri_External_Redirect", external_company_url)
                            database.log_job(job_id, company_name, "LOGGED_EXTERNAL_PORTAL")
                            print(f"   | -> [SUCCESS] Embedded portal link into databank ledger queue.")
                            
                            await portal_page.close()
                            await job_page.close()
                            continue

                        await apply_button.click(force=True)
                        await asyncio.sleep(2.5)

                        print(f"   | -> [SUCCESS] Direct application successfully dispatched!")
                        database.log_job(job_id, company_name, "APPLIED_SUCCESS")
                        await job_page.close()

                    except Exception as inner_e:
                        try: await job_page.close()
                        except: pass
                        continue
            except Exception as query_e:
                print(f"[NAUKRI WORKER ERROR] Search thread failure: {query_e}")
                continue
                
        await self.page.close()