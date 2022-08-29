#!/usr/bin/env python3

# Quick exit button evaluation script
#
# Creates an environment for evaluators to automatically work through a list of sites to evaluate
# Stores results in a file for later
from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import os
import random
from time import time_ns
import keyboard

# Globals
# Saved progress filename
state_filename = "./evaluation.json"
sitelist_filename = "./exit_button_sites.csv"
evaluator_name = ""
# URLs
blank_site = "https://www.google.com/blank.html"
survey_url = "https://cambridge.eu.qualtrics.com/jfe/form/SV_8w7NLy1yA3x7A0u"
# Prompt text for each test
btn_prompt = "Please locate and click on the quick exit button on the following website"
shortcut_prompt = "Please locate and press the quick exit shortcut on the following website"
help_prompt = "Please locate and click on the link to the explainer text on the following website"
# Store if browser is currently mobile or desktop
using_mobile = False
# Install and save chrome driver for launching browser instances
os.environ['WDM_LOG_LEVEL'] = '0'  # Silence logs
chrome_driver_service = Service(ChromeDriverManager().install())
# Store websites to evaluate (will be populated on load)
desktop_site_list = []
mobile_site_list = []


# Class for sites that will be evaluated
class Site:
    def __init__(self, url, mobile_site=False, shortcut=None,
                 has_button=True, has_explainer=False, safe_browsing_url=None):
        self.url = url
        self.mobile_site = mobile_site
        self.shortcut = shortcut
        self._has_explainer = has_explainer
        self.safe_browsing_url = safe_browsing_url
        self._has_button = has_button

    # Print string of
    def __str__(self):
        return f'[{"mobile" if self.mobile_site else "desktop"}]{self.url} | ' \
               f'contains [{"button," if self.has_button() else ""}{"shortcut," if self.has_shortcut() else ""}' \
               f'{"explainer," if self.has_explainer() else ""}{"safety" if self.has_safe_browsing_page() else ""}] | '\
               f'shortcut = {self.shortcut if self.has_shortcut() else "N/A"} | ' \
               f'safe browsing page = {self.safe_browsing_url if self.has_safe_browsing_page() else "N/A"} '

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.url == other.url and self.mobile_site == other.mobile_site

    def has_button(self):
        return self._has_button

    def has_shortcut(self):
        return self.shortcut is not None

    def has_explainer(self):
        return self._has_explainer

    def has_safe_browsing_page(self):
        return self.safe_browsing_url is not None


# Expected Condition for an alert to not be present
class AlertIsNotPresent(object):
    def __call__(self, driver):
        try:
            _ = driver.switch_to.alert.text
            return False
        except NoAlertPresentException or WebDriverException:
            return True


# Wait condition for any tab containing the site's explainer text
class AnyTabContainsSafeBrowsingUrl(object):
    def __init__(self, site):
        self._site = site

    def __call__(self, driver):
        for handle in browser.window_handles:
            browser.switch_to.window(handle)
            if self._site.safe_browsing_url in browser.current_url:
                return True
        # else, default to whatever tab we were already in, and return flag indicating it was not found
        else:
            return False


# Open file containing results, progress so far as JSON
def load_state():
    if not os.path.exists(state_filename):
        return "", {}

    with open(state_filename, "r") as f:
        # Parse JSON into dictionary
        data = json.load(f)
    # Parse main variables into dictionary
    name = data["name"]
    evaluated = data["evaluated"]
    return name, evaluated


# Save state to file as JSON
def save_state(name, evaluated):
    # Build json from variables
    state = {
        "name": name,
        "evaluated": evaluated,
    }
    # Convert to JSON and write to file
    with open(state_filename, "w") as f:
        json.dump(state, f)


# Parse site list into arrays of Site-s
def parse_site_list():
    global desktop_site_list, mobile_site_list

    with open(sitelist_filename, "r") as f:
        data = map(lambda l: l.split(","), f.readlines()[1:])

        for site in data:
            # Read fields from CSV
            url = site[0]
            if url == "":
                # blank or analytics row
                continue
            # category = site[1]
            # region = site[2]
            has_desktop_button = site[3] != ""
            has_mobile_button = site[4] != ""
            # shortcut_type = site[5]
            desktop_shortcut = site[6] if site[6] != "" else None
            mobile_shortcut = site[7] if site[7] != "" else None
            explainer_text = site[8] != ""
            safe_browsing_url = site[9] if site[9] != "" else None
            # comments = site[10]

            # Add to relevant list(s)
            if has_desktop_button or desktop_shortcut is not None:
                desktop_site_list.append(Site(
                    url,
                    mobile_site=False,
                    has_button=has_desktop_button,
                    shortcut=desktop_shortcut,
                    has_explainer=explainer_text,
                    safe_browsing_url=safe_browsing_url,
                ))
            if has_mobile_button or mobile_shortcut is not None:
                mobile_site_list.append(Site(
                    url,
                    mobile_site=True,
                    has_button=has_mobile_button,
                    shortcut=mobile_shortcut,
                    has_explainer=explainer_text,
                    safe_browsing_url=safe_browsing_url,
                ))


# Close browser instance safely
def close_browser():
    global browser
    try:
        browser.quit()
    except NameError or AttributeError:
        # Browser not yet instantiated / already closed: no action needed
        pass


# Close all tabs but one
def cleanup_browser():
    global browser
    while len(browser.window_handles) > 1:
        browser.switch_to.window(browser.window_handles[-1])
        browser.close()
    browser.switch_to.window(browser.window_handles[0])


# Find a certain tab
def find_tab(tab_substr):
    global browser
    for handle in browser.window_handles:
        browser.switch_to.window(handle)
        if tab_substr in browser.current_url:
            return True
    # else, default to whatever tab we were already in, and return flag indicating it was not found
    else:
        return False

# Make a mobile browser
def mobile_browser():
    global browser, using_mobile
    close_browser()

    width = 360
    height = 640
    mobile_emulation = {
        "deviceMetrics": {"width": width, "height": height, "pixelRatio": 3.0},
        "userAgent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/99.0.4844.84 Mobile Safari/537.36"}
    options = Options()
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    browser = Chrome(service=chrome_driver_service, options=options)
    browser.set_window_size(width, height+150)
    using_mobile = True
    return browser


# Make a desktop browser
def desktop_browser():
    global browser, using_mobile
    close_browser()
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    browser = Chrome(service=chrome_driver_service, options=options)
    using_mobile = False
    return browser


# Get a page and wait for it to load
def load_page(url):
    browser.get(url)
    _ = WebDriverWait(browser, 36000).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# Show an alert and wait for it to be closed
def alert(text):
    browser.execute_script("alert('" + text + "')")
    _ = WebDriverWait(browser, 36000).until(AlertIsNotPresent())


# Listen for sequence of keypresses
def listen_for(keys):
    wait_for = keys.split("+")
    history = []
    while history[-len(wait_for):] != wait_for:
        history.append(keyboard.read_key())


# Wait for page to change to a different domain
def run_exit_test(site, alert_msg):
    global browser
    load_page(site.url)
    alert(alert_msg)
    start = time_ns()
    end = start
    try:
        _ = WebDriverWait(browser, 36000).until(
            lambda d: site.url not in d.current_url and
                      site.url.replace("www.","") not in d.current_url and
                      site.url.replace("://","://www.") not in d.current_url
        )
        end = time_ns()
    except KeyboardInterrupt:
        end = start - 1.0
    except:
        end = time_ns()
    finally:
        cleanup_browser()
        return (end - start) / (10 ** 9)


# Wait for specific page to be loaded
def run_explainer_test(site, alert_msg):
    global browser
    load_page(site.url)
    alert(alert_msg)
    start = time_ns()
    end = start
    try:
        _ = WebDriverWait(browser, 36000).until(
            AnyTabContainsSafeBrowsingUrl(site)
        )
        end = time_ns()
    except KeyboardInterrupt:
        end = start - 1.0
    except:
        end = time_ns()
    finally:
        cleanup_browser()
        return (end - start) / (10 ** 9)


# Evaluate a single website
def evaluate_website(site):
    global browser, evaluator_name
    res = {
        "url": site.url,
        "is_mobile": site.mobile_site,
    }
    # Switch to appropriate browser
    if site.mobile_site and not using_mobile:
        mobile_browser()
    elif not site.mobile_site and using_mobile:
        desktop_browser()

    # RUN TIMING TESTS
    # Button click test
    if site.has_button():
        res["learn_button_time"] = run_exit_test(site, 'Please find and click the quick exit button')
    # Shortcut tests
    if site.has_shortcut():
        res["learn_shortcut_time"] = run_exit_test(site, 'Please find and type the quick exit keyboard shortcut')
    # Locate explainer text
    if site.has_safe_browsing_page():
        res["learn_explainer_time"] = run_explainer_test(site, 'Please find and go to the safe browsing information page')

    # Reset site for evaluator to view
    load_page(site.url)
    # Load site evaluation survey
    browser.execute_script(f"window.open('{survey_url}');")
    find_tab("qualtrics")

    # Autofill first page (evaluator & site info)
    try:
        # Wait for first page to fully load
        _ = WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, 'QR~QID1'))
        )
        # Find each element and enter relevant info
        browser.find_element(By.ID, value='QR~QID1').send_keys(evaluator_name)
        browser.find_element(By.ID, value='QR~QID2').send_keys(site.url)
        if site.mobile_site:
            browser.find_element(By.ID, value='QID4-2-label').click()  # "Mobile"
        else:
            browser.find_element(By.ID, value='QID4-1-label').click()  # "Desktop"
        # Submit info page
        browser.find_element(By.ID, value='NextButton').click()
        # Wait for second page to load
        _ = WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, 'QID5'))
        )
    except TimeoutException:
        input('Please enter your details into the web form, then press <enter> here when done.')

    # Autofill N/A options on Likert scales
    if not site.has_button():
        browser.find_element(By.ID, value='QID3-6-label').click()
        browser.find_element(By.ID, value='QID6-6-label').click()
    if not site.has_shortcut():
        browser.find_element(By.ID, value='QID7-6-label').click()
        browser.find_element(By.ID, value='QID8-6-label').click()
    if not site.has_explainer():
        browser.find_element(By.ID, value='QID9-6-label').click()
        browser.find_element(By.ID, value='QID10-6-label').click()
    if not site.has_safe_browsing_page():
        browser.find_element(By.ID, value='QID11-6-label').click()
    # Scroll back to the top
    browser.execute_script('window.scrollTo(0, 0);')
    # Wait for page submit
    try:
        _ = WebDriverWait(browser, 36000).until(
            EC.presence_of_element_located((By.ID, 'EndOfSurvey'))
        )
    except Exception as e:
        print(e, 'Form not completed in time; erroring...')
        raise e

    # Close survey and any extra tabs
    cleanup_browser()

    # RUN MEMORABILITY TIMING TESTS
    # Button click test
    if site.has_button():
        res["recall_button_time"] = run_exit_test(site, 'Please find and click the quick exit button')
    # Shortcut tests
    if site.has_shortcut():
        res["recall_shortcut_time"] = run_exit_test(site, 'Please find and type the quick exit keyboard shortcut')
    # Locate explainer text
    if site.has_safe_browsing_page():
        res["recall_explainer_time"] = run_explainer_test(site, 'Please find and go to the safe browsing information page')

    # Return results for this site
    return res


def evaluate_all():
    global browser, evaluator_name
    # Create globals and session variables
    # Recover save state from previous session if present
    evaluator_name, evaluated = load_state()
    for completed_site in evaluated:
        mobile = completed_site["is_mobile"]
        cs = Site(completed_site["url"], mobile)
        if not mobile and cs in desktop_site_list:
            desktop_site_list.remove(cs)
        elif mobile and cs in mobile_site_list:
            mobile_site_list.remove(cs)
    print(f"You have {len(desktop_site_list)} desktop sites and {len(mobile_site_list)} mobile sites remaining.")

    if "" == evaluator_name:
        # First time setup
        evaluator_name = input("Please enter your name:\n > ")
        evaluated = []

    # Randomise order of sites to evaluate
    random.shuffle(desktop_site_list)
    random.shuffle(mobile_site_list)

    # Run desktop site tests
    if 0 != len(desktop_site_list):
        desktop_browser()
        for site in desktop_site_list:
            res = evaluate_website(site)
            evaluated.append(res)
            save_state(evaluator_name, evaluated)
            # Clear site and allow pause / exit
            try:
                cleanup_browser()
                load_page(blank_site)
                alert(f'Saved results for {site.url} [desktop]'
                      '\\nPlease press enter / click OK when ready to continue with the next site.'
                      '\\nYou can close the browser to save progress for later.')
            except WebDriverException:
                print("Progress saved. Exiting...")
                return

    # Run mobile site tests
    if 0 != len(mobile_site_list):
        mobile_browser()
        for site in mobile_site_list:
            res = evaluate_website(site)
            evaluated.append(res)
            save_state(evaluator_name, evaluated)
            # Clear site and allow pause / exit
            try:
                cleanup_browser()
                load_page(blank_site)
                alert(f'Saved results for {site.url} [mobile]'
                      '\\nPlease press enter / click OK when ready to continue with the next site.'
                      '\\nYou can close the browser to save progress for later.')
            except WebDriverException:
                print("Progress saved. Exiting...")
                return

    print("You have now evaluated all sites. Thank you!\n"
          "Please send me the evaluation.json which contains your results.")


if __name__ == '__main__':
    print("""Welcome to the quick exit button evaluator!

You will be asked to locate the quick exit buttons (and where applicable, exit shortcuts and safe browsing information) 
for a variety of websites. In each case, an alert will pop up after the site loads asking you to click the button / 
type the shortcut / locate the safe browsing page. The time between closing the alert and completing the action will be
recorded for each action required on the site.

After this, a short survey will load, asking you to rate the usability of each relevant component through several likert
scales and optional additional comments boxes. This may also ask about explainer texts, which inform the user about
the exit buttons/shortcuts when they load the page. Please complete the relevant parts of this survey. The first page
of the survey and any relevant N/A options should be autofilled.

After completing the survey, you will be asked to re-locate the same elements as before. The purpose of this is to test
the memorability of each component (whereas the first time evaluates the learnability).

A blank page will show between each site, with an alert that waits to be closed before continuing. This allows you to
take a break, or to close the browser and save your progress for later.
""")
    parse_site_list()
    # desktop_site_list = list(filter(lambda s: s.has_shortcut(), desktop_site_list))  # Shortcut sites only
    # print("\n".join(map(str, desktop_site_list)), "\n------------\n", "\n".join(map(str, mobile_site_list)))
    print(f"{len(desktop_site_list)} desktop sites and {len(mobile_site_list)} mobile sites loaded.")
    evaluate_all()
    close_browser()
