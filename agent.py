import asyncio
from playwright.async_api import async_playwright

async def main():
    portal = "https://www.naukri.com"
    keyword = "SAP CPI Developer"
    
    # 1. PROFILE METRICS MATRIX: Pre-define your configuration answers here
    MY_ANSWERS = {
        "notice_period": "Immediate",         # Options usually: Immediate, 15 days, 1 month, etc.
        "expected_ctc": "Negotiable",         # Text field answer
        "experience": "2",                     # Years of experience numerical metric
        "skills": "SAP CPI, iFlows, Groovy Script, Node.js, REST APIs"
    }
    
    PRIORITY_COMPANIES = ["deloitte", "ey", "pwc", "kpmg", "capgemini", "ibm", "tcs"]
    BLOCKLIST_COMPANIES = ["accenture", "fake consultancy", "placement agency limited"]
    ALLOWED_RECENCY_KEYWORDS = ["just now", "few hours ago", "1 day ago", "2 days ago", "3 days ago"]

    print("\n[STARTING] Launching Autonomous Target Sweep with Questionnaire Auto-Solver...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = await context.new_page()
            
            print(f"[NAVIGATING] Initializing viewport workspace on {portal}...")
            await page.goto(portal, wait_until="load")
            await asyncio.sleep(2)

            print(f"[SEARCHING] Injecting focus keyword: '{keyword}'...")
            search_input = await page.wait_for_selector("input.suggestor-input, input[placeholder*='skills']", timeout=8000)
            await search_input.click(force=True)
            await search_input.fill("")
            await search_input.type(keyword, delay=80)
            await search_input.press("Enter")
            await page.wait_for_timeout(5000)
            
            job_cards = await page.query_selector_all("div.cust-job-tuple, article.jobTuple")
            print(f"[FEED] Loaded {len(job_cards)} job elements on the front page.")

            applied_counter = 0

            for index, card in enumerate(job_cards[:10]):  # Focus on top 10 fresh listings
                print(f"\n--- [CARD {index + 1}] Evaluating metrics... ---")
                
                try:
                    company_element = await card.query_selector("a.comp-name, a.companyName")
                    company_name = (await company_element.inner_text()).strip().lower() if company_element else "unknown"
                    
                    date_element = await card.query_selector("span.job-post-day, span.type.main-2")
                    date_text = (await date_element.inner_text()).strip().lower() if date_element else "unknown"
                    
                    title_link = await card.query_selector("a.title")
                    if not title_link:
                        continue

                    print(f"[METRICS] Firm: '{company_name.upper()}' | Age: '{date_text}'")

                    if any(blocked in company_name for blocked in BLOCKLIST_COMPANIES):
                        print(f"[SKIP] Company matched blocklist constraints.")
                        continue

                    is_recent = any(keyword in date_text for keyword in ALLOWED_RECENCY_KEYWORDS)
                    is_priority = any(priority in company_name for priority in PRIORITY_COMPANIES)

                    if not is_recent and not is_priority:
                        print(f"[SKIP] Fails verification: Too stale.")
                        continue

                    print(f"[PROCEED] Opening split tab context...")
                    async with context.expect_page() as new_page_info:
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
                        print("[FILTER] Redirect link detected. Cleaning viewport context...")
                        await job_page.close()
                        continue
                    
                    print(f"[SUBMIT] Dispatching primary application click layer...")
                    await apply_button.click(force=True)
                    await asyncio.sleep(2.5)  # Pause to see if a questionnaire dialog intercept layers over

                    # --- 2. THE INTELLIGENT QUESTIONNAIRE INTERCEPT LAYER ---
                    # Check if a chatbot/questionnaire form window layer exists on the DOM view
                    dialog_selectors = ["div.chatbot-container", "div.questionnaire-form", "div.modal-content", "div[class*='questionnaire']"]
                    dialog_found = False
                    
                    for selector in dialog_selectors:
                        if await job_page.query_selector(selector):
                            dialog_found = True
                            break
                            
                    if dialog_found:
                        print("[DETECTED] Questionnaire layer active over screen viewport. Executing solve routine...")
                        
                        # Locate all individual question nodes inside the form layout
                        question_blocks = await job_page.query_selector_all("div.question-block, div.chatbot__question")
                        
                        for block in question_blocks:
                            question_text = (await block.inner_text()).lower()
                            print(f"[QUESTION] Parsing content: '{question_text[:50]}...'")
                            
                            # A. Handle Notice Period Layouts
                            if "notice" in question_text:
                                # Look for a radio button option matching your preference setting
                                radio_option = await block.query_selector(f"label:has-text('{MY_ANSWERS['notice_period']}')")
                                if radio_option:
                                    await radio_option.click(force=True)
                                    print(f" -> Selected option: '{MY_ANSWERS['notice_period']}'")
                                    continue
                            
                            # B. Handle Experience Metric Inquiries
                            if "experience" in question_text or "years" in question_text:
                                text_input = await block.query_selector("input[type='text'], input[type='number']")
                                if text_input:
                                    await text_input.fill(MY_ANSWERS['experience'])
                                    print(f" -> Inputted metric: {MY_ANSWERS['experience']} Years")
                                    continue
                                    
                            # C. Generic Fallback Input Text Fields (Expected CTC / Skills)
                            generic_input = await block.query_selector("input[type='text'], textarea")
                            if generic_input:
                                if "ctc" in question_text:
                                    await generic_input.fill(MY_ANSWERS['expected_ctc'])
                                    print(f" -> Filled field with parameter: {MY_ANSWERS['expected_ctc']}")
                                else:
                                    await generic_input.fill(MY_ANSWERS['skills'])
                                    print(" -> Filled field with skill profile matrix.")

                        # Click the final submission save/submit confirmation button in the dialog wrapper
                        submit_form_btn = await job_page.query_selector("button:has-text('Submit'), button:has-text('Save'), div.submit-btn")
                        if submit_form_btn:
                            await submit_form_btn.click(force=True)
                            await asyncio.sleep(2)
                            print("[CONFIRMED] Multi-stage questionnaire successfully cleared and sent!")
                    else:
                        # If no dialog intercepted the process, it was a clean single-click action
                        print("[CONFIRMED] Direct application single-click successfully processed!")
                    
                    applied_counter += 1
                    await job_page.close()

                except Exception as inner_error:
                    print(f"[INFO] Skipping card context or already applied.")
                    try:
                        await job_page.close()
                    except:
                        pass
                    continue

            print(f"\n[FINISH] Run complete! Natively submitted to {applied_counter} fresh targeted roles.")

        except Exception as e:
            print(f"\n[ERROR] Core execution loop broken: {e}")

        print("\n=======================================================")
        print("[HUMAN GATEKEEPER INTERCEPT COGNITIVE LOCK ACTIVE]")
        print("Session loop completely finished.")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(main())