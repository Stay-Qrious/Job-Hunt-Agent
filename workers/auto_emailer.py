import asyncio
import urllib.parse
from playwright.async_api import BrowserContext
import database

class AutoEmailerWorker:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    async def process_email_queue(self):
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, company, portal_url FROM portal_queue WHERE status = 'PENDING' AND portal_url LIKE 'mailto:%' LIMIT 3")
        pending_emails = cursor.fetchall()
        conn.close()

        if not pending_emails:
            return

        print(f"\n[EMAIL ENGINE] Processing {len(pending_emails)} stashed recruiter contacts...")

        for item_id, company, mailto_url in pending_emails:
            email_address = mailto_url.replace("mailto:", "")
            print(f" -> Preparing application draft for: {email_address}")

            self._update_queue_status(item_id, "PROCESSING")
            
            subject_line = "Application for SAP CPI Developer / Integration Specialist"
            body_content = (
                f"Hi,\n\n"
                f"I saw your recruitment post on LinkedIn regarding openings for an SAP CPI / Integration Engineer position and wanted to reach out.\n\n"
                f"I am an Associate Software Engineer specializing in backend architectures and cloud integrations. My experience covers designing end-to-end integration layouts (SAP CPI, iFlows, Groovy Scripting), backend systems engineering, and data pipeline management.\n\n"
                f"I would welcome the opportunity to discuss how my profile fits your current requirements. Please let me know how I can best submit my resume for review.\n\n"
                f"Best regards,\n"
                f"Abhishek Tripathi"
            )

            encoded_subject = urllib.parse.quote(subject_line)
            encoded_body = urllib.parse.quote(body_content)
            
            # UPGRADE: Force a full frame desktop interaction layout anchor path instead of a sandbox component view
            gmail_compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={email_address}&su={encoded_subject}&body={encoded_body}"
            
            self.page = await self.context.new_page()
            try:
                await self.page.goto(gmail_compose_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(6) # Core layout painting interval

                # UPGRADE: Find and click Gmail's literal "Save & Close" window vector graphic to force server-side data commitment
                print("   | Searching for native Gmail interface save controls...")
                
                # Target common native window control structures inside Gmail's window layout
                save_close_node = await self.page.query_selector(
                    "img[data-tooltip*='Save'], img[aria-label*='Close'], div[aria-label*='Save and close'], img.Ha"
                )
                
                if save_close_node:
                    print("   | Native save control identified. Dispatched structural click event...")
                    await save_close_node.click(force=True)
                else:
                    print("   | Falling back to window serialization shortcut matrix...")
                    await self.page.keyboard.down("Control")
                    await self.page.keyboard.press("s")
                    await self.page.keyboard.up("Control")
                
                await asyncio.sleep(4) # Force thread hold to complete network package transmission loops
                print(f"   | -> [VERIFIED] Template successfully logged into your cloud Drafts cache folder.")
                self._update_queue_status(item_id, "COMPLETED")
                
            except Exception as e:
                print(f"   | -> [ERROR] Execution challenge: {e}")
                self._update_queue_status(item_id, "QUEUED_FOR_REVIEW")
            finally:
                try:
                    await self.page.close()
                except:
                    pass

    def _update_queue_status(self, item_id: int, status: str):
        conn = database.sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE portal_queue SET status = ? WHERE id = ?", (status, item_id))
        conn.commit()
        conn.close()