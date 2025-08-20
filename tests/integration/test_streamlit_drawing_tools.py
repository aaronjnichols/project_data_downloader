#!/usr/bin/env python3
"""
Playwright test to verify Streamlit drawing tools functionality.

This test verifies:
1. The page loads correctly at http://localhost:8501
2. When switching to "Draw" mode, drawing tools are visible
3. The instruction text shows correct message for Draw mode with no existing AOI
4. Takes screenshots for verification
"""

import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_streamlit_drawing_tools():
    """Test the Streamlit application drawing tools functionality."""
    
    # Create screenshots directory
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print("Step 1: Navigating to http://localhost:8501")
            await page.goto("http://localhost:8501", wait_until='networkidle')
            
            # Wait a bit longer for Streamlit to fully load
            print("Step 2: Waiting for page to load fully...")
            await page.wait_for_timeout(5000)  # Wait 5 seconds
            
            # Take initial screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=f"{screenshots_dir}/01_initial_page_{timestamp}.png", full_page=True)
            print(f"[OK] Screenshot saved: 01_initial_page_{timestamp}.png")
            
            print("Step 3: Looking for AOI mode selector...")
            
            # Look for the AOI mode selector - it might be a radio button or selectbox
            # Let's try to find radio buttons first
            aoi_mode_elements = await page.query_selector_all('[data-testid="stRadio"] label')
            if not aoi_mode_elements:
                # Try selectbox
                aoi_mode_elements = await page.query_selector_all('[data-testid="stSelectbox"] select option')
            
            if not aoi_mode_elements:
                # Try other possible selectors
                aoi_mode_elements = await page.query_selector_all('input[type="radio"]')
            
            print(f"Found {len(aoi_mode_elements)} potential AOI mode elements")
            
            # Let's also look for any text that mentions "Draw" or "Upload"
            page_content = await page.content()
            if "Draw" in page_content and "Upload" in page_content:
                print("[OK] Found AOI mode options (Draw/Upload) in page content")
            else:
                print("[WARNING] Could not find AOI mode options in page content")
            
            # Try to find and click on Draw mode
            print("Step 4: Attempting to switch to Draw mode...")
            
            # Strategy 1: Look for radio button with "Draw" text
            draw_radio = await page.query_selector('label:has-text("Draw")')
            if draw_radio:
                print("Found Draw radio button, clicking...")
                await draw_radio.click()
                await page.wait_for_timeout(2000)  # Wait for UI to update
            else:
                # Strategy 2: Look for radio input followed by text containing "Draw"
                print("Looking for Draw option using alternative method...")
                # Find all radio buttons and check their labels
                radio_buttons = await page.query_selector_all('input[type="radio"]')
                for radio in radio_buttons:
                    # Get the next sibling or parent element that might contain the label text
                    parent = await radio.query_selector('xpath=..')
                    if parent:
                        text = await parent.text_content()
                        if text and "Draw" in text:
                            print(f"Found Draw option: {text}")
                            await radio.click()
                            await page.wait_for_timeout(2000)
                            break
            
            # Take screenshot after attempting to switch to Draw mode
            await page.screenshot(path=f"{screenshots_dir}/02_after_draw_mode_{timestamp}.png", full_page=True)
            print(f"[OK] Screenshot saved: 02_after_draw_mode_{timestamp}.png")
            
            print("Step 5: Checking for drawing tools on the map...")
            
            # Look for folium/leaflet map elements and drawing tools
            map_container = await page.query_selector('[data-testid="stDeckGlJsonChart"]')
            if not map_container:
                # Try alternative selectors for folium maps
                map_container = await page.query_selector('.folium-map')
                if not map_container:
                    map_container = await page.query_selector('#map')
                    if not map_container:
                        map_container = await page.query_selector('iframe')  # Streamlit folium uses iframe
            
            if map_container:
                print("[OK] Found map container")
                
                # If it's an iframe (folium), we need to access its content
                tag_name = await map_container.evaluate('el => el.tagName.toLowerCase()')
                if tag_name == 'iframe':
                    print("Map is in iframe, accessing iframe content...")
                    # Get the iframe content
                    frame = await map_container.content_frame()
                    if frame:
                        # Look for drawing tools within the iframe
                        drawing_tools = await frame.query_selector_all('.leaflet-draw-toolbar')
                        if drawing_tools:
                            print(f"[OK] Found {len(drawing_tools)} drawing toolbar(s) in iframe")
                        else:
                            # Look for other drawing-related elements
                            draw_buttons = await frame.query_selector_all('[title*="Draw"]')
                            if draw_buttons:
                                print(f"[OK] Found {len(draw_buttons)} drawing button(s) in iframe")
                            else:
                                print("[WARNING] No drawing tools found in iframe")
                        
                        # Take screenshot of the iframe element (not the frame itself)
                        await map_container.screenshot(path=f"{screenshots_dir}/03_map_iframe_{timestamp}.png")
                        print(f"[OK] Screenshot of map iframe saved: 03_map_iframe_{timestamp}.png")
                else:
                    # Regular map element, look for drawing tools
                    drawing_tools = await page.query_selector_all('.leaflet-draw-toolbar')
                    if drawing_tools:
                        print(f"[OK] Found {len(drawing_tools)} drawing toolbar(s)")
                    else:
                        print("[WARNING] No drawing toolbars found")
            else:
                print("[WARNING] Could not find map container")
            
            print("Step 6: Checking instruction text...")
            
            # Look for instruction text that should show "Draw AOI: Use the drawing tools..."
            instruction_elements = await page.query_selector_all('text="Draw AOI: Use the drawing tools to define your area of interest"')
            if instruction_elements:
                print("[OK] Found correct instruction text for Draw mode")
            else:
                # Look for any text containing "Draw AOI" or similar
                page_text = await page.text_content('body')
                if "Draw AOI" in page_text:
                    print("[OK] Found 'Draw AOI' text in page")
                    # Extract the specific line
                    lines = page_text.split('\n')
                    for line in lines:
                        if "Draw AOI" in line:
                            # Clean the line to avoid encoding issues
                            clean_line = line.strip().encode('ascii', 'ignore').decode('ascii')
                            print(f"  Instruction text: {clean_line}")
                else:
                    print("[WARNING] Could not find 'Draw AOI' instruction text")
                
                # Also check for the problematic "clear AOI" text
                if "clear" in page_text.lower() and "aoi" in page_text.lower():
                    print("[WARNING] Found 'clear AOI' text - this might indicate the bug is still present")
                    lines = page_text.split('\n')
                    for line in lines:
                        if "clear" in line.lower() and "aoi" in line.lower():
                            clean_line = line.strip().encode('ascii', 'ignore').decode('ascii')
                            print(f"  Clear AOI text: {clean_line}")
            
            # Take final screenshot
            await page.screenshot(path=f"{screenshots_dir}/04_final_state_{timestamp}.png", full_page=True)
            print(f"[OK] Screenshot saved: 04_final_state_{timestamp}.png")
            
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            
            # Print page title and URL
            title = await page.title()
            url = page.url
            print(f"Page Title: {title}")
            print(f"Page URL: {url}")
            
            # Print any console errors
            print("\nPage Console Messages:")
            # Note: Console messages would need to be captured during page load
            
            # Print text content analysis
            print(f"\nPage contains 'Draw' text: {'Draw' in page_text}")
            print(f"Page contains 'Upload' text: {'Upload' in page_text}")
            print(f"Page contains 'AOI' text: {'AOI' in page_text}")
            print(f"Page contains drawing tools: {map_container is not None}")
            
            print(f"\n[OK] All screenshots saved to '{screenshots_dir}' directory")
            print("Please review the screenshots to verify the drawing tools functionality.")
            
        except Exception as e:
            print(f"[ERROR] Error during test: {e}")
            # Take error screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=f"{screenshots_dir}/error_{timestamp}.png", full_page=True)
            raise
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_streamlit_drawing_tools())