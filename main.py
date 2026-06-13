import asyncio
from playwright.async_api import async_playwright
import database
import config
from workers.naukri_worker import NaukriWorker
from workers.linkedin_feed_worker import LinkedInFeedWorker
from workers.placement_officer_worker import PlacementOfficerWorker
from workers.link_explorer_agent import LinkExplorerAgent

async def main():
    print("\n=======================================================")
    print("      INITIALIZING AUTONOMOUS INTEL DATA HARVEST MATRIX")
    print("=======================================================")
    
    database.init_db()

    async with async_playwright() as p:
        try:
            print("[ORCHESTRATOR] Hooking browser framework automation on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            
            # --- PHASE 1: TARGETED SPECIALIZATION NAUKRI SWEEP ---
            print("\n--- [PHASE 1] RUNNING LIVE NAUKRI APPLICATION CONTEXT ---")
            naukri_engine = NaukriWorker(context)
            await naukri_engine.run_sweep()
            
            # --- PHASE 2: PLACEMENT HUB TRACKING ---
            print("\n--- [PHASE 2] SCRAPING LATEST OFF-CAMPUS PLACEMENT AGGREGATORS ---")
            placement_hub = PlacementOfficerWorker(context)
            await placement_hub.scrape_latest_drives()

            # --- PHASE 3: MULTI-ENTERPRISE BRAND SOCIAL MATRIX ---
            print("\n--- [PHASE 3] RUNNING MULTI-ENTERPRISE LINKEDIN SOCIAL GRID SCANNER ---")
            feed_hunter = LinkedInFeedWorker(context)
            # Cycles through your big-brand target company array lists
            for company_keyword in config.BRAND_KEYWORDS:
                await feed_hunter.scan_social_feed(company_keyword)
                await asyncio.sleep(2)
                
            # --- PHASE 4: DEEP LINK EXTROLLER EXPLORER & FORM FILLER ---
            print("\n--- [PHASE 4] DEPLOYING DEEP LINK EXTRACTION & FILL WORKERS ---")
            deep_explorer = LinkExplorerAgent(context)
            await deep_explorer.process_discovery_queue()
                
        except Exception as e:
            print(f"\n[CRITICAL FRAMEWORK FAULT] Orchestrator loop broke: {e}")

    print("\n=======================================================")
    print("      SWEEP MATRIX DATA INGESTION SEQUENCE RUN COMPLETE")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(main())