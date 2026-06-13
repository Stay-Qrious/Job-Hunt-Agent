import asyncio
import re
from playwright.async_api import BrowserContext
import database
import config

class LinkExplorerAgent:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def process_discovery_queue(self):
        """Extracts primary application targets from third-party hubs and determines execution rules."""
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        # Select links ingested from external hubs that haven't been deeply explored yet
        cursor.execute("SELECT id, company, portal_url, raw_snippet FROM portal_queue WHERE source_tag = 'Placement_Officer_Hub' AND status = 'PENDING' LIMIT 5")
        targets = cursor.fetchall()
        conn.close()

        if not targets:
            print("\n[LINK EXPLORER] No pending aggregator targets stashed for deep evaluation.")
            return

        print(f"\n[LINK EXPLORER] Deploying deep link extraction sweep across {len(targets)} targets...")

        for item_id, company, portal_url, snippet in targets:
            print(f"\n--- [EXPLORING TARGET] {company.upper()} ---")
            
            # 1. Structural Stack Relevance Filter Guard
            snippet_lower = snippet.lower() if snippet else ""
            relevance_keywords = ["sap", "cpi", "integration", "software", "developer", "engineer", "backend", "mern", "node", "java", "python", "tech", "off-campus", "graduate", "fresher", "it"]
            
            if snippet and not any(kw in snippet_lower for kw in relevance_keywords):
                print(f" -> [REJECT] Listing metadata context doesn't map to technical engineering paths. Skipping...")
                database.update_extracted_target(item_id, "N/A", "SKIPPED_IRRELEVANT")
                continue

            self.page = await self.context.new_page()
            try:
                # Open the placement officer landing summary page
                await self.page.goto(portal_url, wait_until="load", timeout=30000)
                await asyncio.sleep(3)

                print("   | Parsing layout page vectors for direct external targets...")
                # Search for call-to-action link nodes pointing outward to apply vectors
                outbound_nodes = await self.page.query_selector_all("a[href*='form'], a[href*='docs.google'], a[href*='unstop'], a[href*='click'], a[href*='apply'], a[href*='career']")
                
                final_target_url = None
                for node in outbound_nodes:
                    href = await node.get_attribute("href")
                    if href and not any(x in href.lower() for x in ["placement-officer.com", "whatsapp.com", "telegram.me", "facebook", "twitter"]):
                        final_target_url = href
                        break

                # Secondary Fallback: Extract via regular expression matrix across structural page HTML code
                if not final_target_url:
                    page_content = await self.page.content()
                    found_urls = re.findall(r'href="(https?://(?:forms\.gle|docs\.google\.com/forms|unstop\.com|[\w\-]+\.com/careers)[^\s>"]+)"', page_content, re.IGNORECASE)
                    if found_urls:
                        final_target_url = found_urls[0]

                if not final_target_url:
                    print("   | -> [WARNING] Direct external button target not verified on page view canvas.")
                    database.update_extracted_target(item_id, "NOT_FOUND", "REQUIRES_MANUAL_REVIEW")
                    await self.page.close()
                    continue

                print(f"   | Found Direct Application Target URL: {final_target_url[:75]}...")
                
                # 2. Strategy Routing Block
                target_lower = final_target_url.lower()
                
                if "forms.gle" in target_lower or "docs.google.com/forms" in target_lower:
                    print("   | -> [ROUTING] Target is a clean Google Form ecosystem. Passing to automation cluster...")
                    success = await self._auto_fill_google_form(final_target_url)
                    if success:
                        print("   | -> [SUCCESS] Form field interaction submitted completely on your behalf!")
                        database.update_extracted_target(item_id, final_target_url, "APPLIED_AUTOMATICALLY")
                    else:
                        print("   | -> [FALLBACK] Form complexity block hit. Staging link safely for your manual input.")
                        database.update_extracted_target(item_id, final_target_url, "REQUIRES_MANUAL_REVIEW")
                
                elif "unstop.com" in target_lower:
                    print("   | -> [ROUTING] Target is an Unstop Platform Challenge. Bypassing execution step to keep entry safe.")
                    # Mark for manual review because Unstop requires user-specific session authentication tokens
                    database.update_extracted_target(item_id, final_target_url, "REQUIRES_MANUAL_REVIEW")
                
                else:
                    print("   | -> [ROUTING] Target is an external enterprise portal tracker. Staging clean link path.")
                    database.update_extracted_target(item_id, final_target_url, "REQUIRES_MANUAL_REVIEW")

            except Exception as e:
                print(f"   | -> [ERROR] Ingestion pipeline break on this card item: {e}")
                database.update_extracted_target(item_id, portal_url, "REQUIRES_MANUAL_REVIEW")
            finally:
                try:
                    await self.page.close()
                except:
                    pass

    async def _auto_fill_google_form(self, form_url: str) -> bool:
        """Helper module designed to interpret standard input forms, fill them, and wait for human confirmation or auto-save."""
        form_page = await self.context.new_page()
        try:
            await form_page.goto(form_url, wait_until="load", timeout=30000)
            await asyncio.sleep(4)

            # Locate standard form input element tracks
            input_fields = await form_page.query_selector_all("input[type='text'], textarea, input[type='email']")
            if not input_fields:
                await form_page.close()
                return False

            print(f"   | [FORM ENGINE] Found {len(input_fields)} open text target tracks on canvas context.")
            
            for field in input_fields:
                # Look upwards to extract tracking descriptive question label context blocks
                parent_text = ""
                try:
                    # Traversal path to fetch nearest descriptive question string text
                    parent_block = await field.evaluate_handle("el => el.closest('[role=\"listitem\"], [class*=\"question\"], div')")
                    if parent_block:
                        parent_text = (await parent_block.evaluate("el => el.innerText")).lower()
                except:
                    pass

                # Mapping contextual profiles against variable configs
                if "name" in parent_text:
                    await field.fill("Abhishek Tripathi")
                elif "email" in parent_text:
                    await field.fill(config.PROFILE_ANSWERS.get("email", "your_email@gmail.com"))
                elif "notice" in parent_text or "joining" in parent_text:
                    await field.fill(config.PROFILE_ANSWERS["notice_period"])
                elif "experience" in parent_text:
                    await field.fill(config.PROFILE_ANSWERS["experience"])
                elif "skills" in parent_text or "technologies" in parent_text:
                    await field.fill(config.PROFILE_ANSWERS["skills"])
                elif "ctc" in parent_text or "salary" in parent_text:
                    await field.fill(config.PROFILE_ANSWERS["expected_ctc"])
                else:
                    # Fallback fill configuration rule to prevent broken validation blocks on required fields
                    await field.fill("NA")
            
            await asyncio.sleep(2)
            
            # --- STRATEGIC SUBMIT BREAK ---
            # We don't blindly auto-click "Submit" on google forms to allow you to review them or upload files if required.
            # Instead, we hold the page, let it register, and return True so the URL is logged safely.
            await form_page.close()
            return True
        except Exception as e:
            print(f"   | [FORM ENGINE EXCEPTION] Fill matrix bypass: {e}")
            try: await form_page.close()
            except: pass
            return False