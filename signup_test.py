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
RUNS = max(1, min(int(os.environ.get("RUNS", "1") or "1"), 5))  # safety cap: max 5
DEBUG = os.environ.get("DEBUG_MODE", "0") == "1"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
SUCCESS_TEXT = os.environ.get("SUCCESS_TEXT", "").strip()  # optional: success page par dikhne wala text


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
            "| name:", el.get_attribute("name"),
            "| id:", el.get_attribute("id"),
            "| type:", el.get_attribute("type"),
            "| placeholder:", el.get_attribute("placeholder"),
            "| text:", el.text,
        )


def find_field(driver, kind):
    """Page ke visible input me se sahi field dhoondhta hai."""
    inputs = [e for e in driver.find_elements(By.TAG_NAME, "input") if e.is_displayed()]

    def attrs(e):
        return " ".join(
            (e.get_attribute(a) or "").lower() for a in ("name", "id", "placeholder", "type")
        )

    if kind == "password":
        for e in inputs:
            if (e.get_attribute("type") or "").lower() == "password":
                return e
    elif kind == "phone":
        for e in inputs:
            a = attrs(e)
            if (e.get_attribute("type") or "").lower() == "tel" or any(
                k in a for k in ("phone", "mobile", "contact", "number")
            ):
                return e
    elif kind == "name":
        for e in inputs:
            a = attrs(e)
            if any(k in a for k in ("name", "fullname", "full_name", "full name")) and "user" not in a:
                return e
        for e in inputs:  # fallback: pehla text input
            if (e.get_attribute("type") or "text").lower() == "text":
                return e
    return None


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

        start_url = driver.current_url

        name_el = find_field(driver, "name")
        phone_el = find_field(driver, "phone")
        pass_el = find_field(driver, "password")

        missing = [k for k, v in (("name", name_el), ("phone", phone_el), ("password", pass_el)) if v is None]
        if missing:
            raise RuntimeError(f"Fields nahi mile: {missing} (DEBUG_MODE=1 chalake dekho)")

        name_el.send_keys(f"Test {rand_str()}")
        phone_el.send_keys("9" + "".join(random.choices(string.digits, k=9)))
        pass_el.send_keys("TestPass@123")

        # Agar confirm password field ho
        pw_fields = [
            e for e in driver.find_elements(By.XPATH, "//input[@type='password']") if e.is_displayed()
        ]
        for extra in pw_fields[1:]:
            extra.send_keys("TestPass@123")

        # Checkbox (terms) ho to tick karo
        for cb in driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
            if cb.is_displayed() and not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)

        submit = driver.find_element(
            By.XPATH,
            "//button[@type='submit'] | //input[@type='submit'] | "
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign') "
            "or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create') "
            "or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]",
        )
        driver.execute_script("arguments[0].click();", submit)

        # Success check
        if SUCCESS_TEXT:
            wait.until(EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{SUCCESS_TEXT}')]")))
        else:
            wait.until(lambda d: d.current_url != start_url)

        ok = True
        print(f"[{i + 1}/{RUNS}] SUCCESS -> {driver.current_url}")
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
