import os
import random
import string
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.environ.get("TEST_URL", "").strip()
RUNS = max(1, min(int(os.environ.get("RUNS", "1") or "1"), 30))  # safety cap: max 30
DEBUG = os.environ.get("DEBUG_MODE", "0") == "1"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
SUCCESS_TEXT = os.environ.get("SUCCESS_TEXT", "").strip()  # optional: signup ke baad dikhne wala text

# Optional overrides
TEST_PHONE = os.environ.get("TEST_PHONE", "").strip()  # fixed phone (sirf pehle run ke liye)
TEST_CITY = os.environ.get("TEST_CITY", "").strip() or "Bhubaneswar"
REFERRAL_CODE = os.environ.get("REFERRAL_CODE", "").strip()  # optional
PASSWORD = os.environ.get("TEST_PASSWORD", "").strip() or "TestPass@123"


def rand_str(n=6):
    return "".join(random.choices(string.ascii_lowercase, k=n))


def make_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=opts)


def dump_page(driver):
    print("URL:", driver.current_url)
    print("TITLE:", driver.title)
    for el in driver.find_elements(By.XPATH, "//input | //button | //select | //textarea"):
        print(
            "TAG:", el.tag_name,
            "| id:", el.get_attribute("id"),
            "| type:", el.get_attribute("type"),
            "| placeholder:", el.get_attribute("placeholder"),
            "| text:", el.text,
        )


def fill(driver, wait, field_id, value):
    el = wait.until(EC.visibility_of_element_located((By.ID, field_id)))
    el.clear()
    el.send_keys(value)
    return el


def open_signup_form(driver, wait):
    """Agar signup form pehle se visible nahi hai to 'Sign Up' tab dabao."""
    try:
        driver.find_element(By.ID, "name").is_displayed() and None
        if driver.find_element(By.ID, "name").is_displayed():
            return
    except Exception:
        pass
    tab = driver.find_element(
        By.XPATH, "//button[normalize-space(.)='Sign Up']"
    )
    driver.execute_script("arguments[0].click();", tab)
    wait.until(EC.visibility_of_element_located((By.ID, "name")))


def run_signup_test(i):
    driver = make_driver()
    wait = WebDriverWait(driver, 20)
    ok = False
    try:
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        time.sleep(2)

        if DEBUG:
            dump_page(driver)
            return True

        open_signup_form(driver, wait)
        start_url = driver.current_url

        phone = TEST_PHONE if (TEST_PHONE and i == 0) else "9" + "".join(random.choices(string.digits, k=9))

        fill(driver, wait, "name", f"Test {rand_str()}")
        fill(driver, wait, "phone", phone)
        fill(driver, wait, "place", TEST_CITY)
        fill(driver, wait, "password", PASSWORD)

        if REFERRAL_CODE:
            fill(driver, wait, "referralCode", REFERRAL_CODE)

        submit = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[@type='submit' and contains(normalize-space(.), 'Create Account')]")
            )
        )
        driver.execute_script("arguments[0].click();", submit)

        # Success check
        if SUCCESS_TEXT:
            wait.until(EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{SUCCESS_TEXT}')]")))
        else:
            wait.until(lambda d: d.current_url != start_url)

        ok = True
        print(f"[{i + 1}/{RUNS}] SUCCESS (phone {phone}) -> {driver.current_url}")
    except Exception as e:
        print(f"[{i + 1}/{RUNS}] FAILED: {type(e).__name__}: {e}")
    finally:
        try:
            driver.save_screenshot(f"result_{i + 1}.png")
        except Exception:
            pass
        driver.quit()
    return ok


if __name__ == "__main__":
    if not BASE_URL.startswith("http"):
        print("TEST_URL secret sahi nahi hai. Poora URL daalo (https://...)")
        sys.exit(1)

    results = []
    for i in range(RUNS):
        results.append(run_signup_test(i))
        if DEBUG:
            break
        time.sleep(5)

    if not all(results):
        sys.exit(1)
