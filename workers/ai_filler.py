import asyncio
from playwright.async_api import BrowserContext
import database
import config

class AIFillerWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def process_queue(self):
        """Pulls pending external portal targets from the ledger and executes AI-driven form filling."""
        # Query our database for up to 3 pending external portal leads to process
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        
        # UPGRADE: Force the form filler to ONLY select actual web portals, completely ignoring mailto links
        cursor.execute(
            "SELECT id, company, portal_url FROM portal_queue WHERE status = 'PENDING' AND portal_url NOT LIKE 'mailto:%' LIMIT 3"
        )
        pending_items = cursor.fetchall()
        conn.close()

        if not pending_items:
            print("\n[AI FILLER] No pending enterprise career portals sitting in the queue channel.")
            return

        print(f"\n[AI FILLER] Initializing form filling loop for {len(pending_items)} queued targets...")
        
        for item_id, company, url in pending_items:
            print(f"\n--- [PROCESSING PORTAL] Company: {company.upper()} ---")
            print(f" -> Target URL: {url[:70]}...")
            
            # Update status flag to prevent dual-worker clashes
            self._update_queue_status(item_id, "PROCESSING")
            self.page = await self.context.new_page()
            
            try:
                await self.page.goto(url, wait_until="load", timeout=20000)
                await asyncio.sleep(5) # Give the complex platform client app time to paint its DOM layout
                
                # --- AI COGNITIVE LAYOUT EVALUATION SEGMENT ---
                # Scrape visible inputs to evaluate what fields are present on the dynamic screen form
                inputs = await self.page.query_selector_all("input, textarea, select")
                print(f" -> Detected {len(inputs)} structural interaction nodes inside the portal viewport.")
                
                form_filled_successfully = False
                
                if "workday" in url or "myworkdayjobs" in url:
                    print(" -> [PLATFORM MATCH] Identified Enterprise Workday Portal Layout.")
                    print("    [ACTION] Staging deep visual agent routing sub-loop...")
                    # Workday configurations require logging in/creating an account first
                    self._update_queue_status(item_id, "REQUIRES_MANUAL_ACCOUNT")
                    await self.page.close()
                    continue

                # --- AUTO FILL ENTRY MATRIX FOR EASY PORTALS & INTEL FORMS ---
                for input_node in inputs:
                    try:
                        # Extract identifying tags to see what the form element is asking for
                        name_attr = (await input_node.get_attribute("name") or "").lower()
                        placeholder_attr = (await input_node.get_attribute("placeholder") or "").lower()
                        id_attr = (await input_node.get_attribute("id") or "").lower()
                        
                        combiner_string = f"{name_attr} {placeholder_attr} {id_attr}"
                        
                        if any(k in combiner_string for k in ["notice", "availability"]):
                            await input_node.fill(config.PROFILE_ANSWERS["notice_period"])
                            print(f"    -> Auto-injected notice period: {config.PROFILE_ANSWERS['notice_period']}")
                            form_filled_successfully = True
                        elif any(k in combiner_string for k in ["ctc", "salary", "expect"]):
                            await input_node.fill(config.PROFILE_ANSWERS["expected_ctc"])
                            print(f"    -> Auto-injected expectations: {config.PROFILE_ANSWERS['expected_ctc']}")
                            form_filled_successfully = True
                        elif any(k in combiner_string for k in ["exp", "year"]):
                            await input_node.fill(config.PROFILE_ANSWERS["experience"])
                            print(f"    -> Auto-injected experience: {config.PROFILE_ANSWERS['experience']} Years")
                            form_filled_successfully = True
                    except:
                        continue
                
                if form_filled_successfully:
                    print(f" -> [SUCCESS] Dynamic parameters mapped into {company.upper()} tracking canvas!")
                    # Locate and trigger the submission button selector matrix
                    submit_node = await self.page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Submit')")
                    if submit_node:
                        # await submit_node.click(force=True) # Uncomment when ready to submit live forms
                        print(" -> [TEST MODE] Application form submission trigger bypassed securely.")
                    
                    self._update_queue_status(item_id, "COMPLETED")
                else:
                    print(" -> [SKIPPED] Form layout requires custom multi-page account creation pipelines.")
                    self._update_queue_status(item_id, "QUEUED_FOR_AGENT_BRAIN")
                
            except Exception as e:
                print(f" -> [ERROR] Failed interacting with portal layout context: {e}")
                self._update_queue_status(item_id, "FAILED_ERROR")
            finally:
                await self.page.close()

    def _update_queue_status(self, item_id: int, status: str):
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE portal_queue SET status = ? WHERE id = ?", (status, item_id))
        conn.commit()
        conn.close()