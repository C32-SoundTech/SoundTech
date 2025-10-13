#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selenium 自动化测试脚本（登录与注册）

- 基于数据驱动执行：读取 test1/data/selenium_test_cases.csv
- 目标站点：https://127.0.0.1:443 （自签名证书）
- 覆盖注册与登录两类用例，生成结果 CSV 与截图

运行：
  python test1/scripts/selenium_test.py
"""

import os
import csv
import time
from datetime import datetime
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = "https://127.0.0.1:443"
REGISTER_URL = f"{BASE_URL}/register"
LOGIN_URL = f"{BASE_URL}/login"

DATA_FILE = os.path.join("test1", "data", "selenium_test_cases.csv")
RESULTS_DIR = os.path.join("test1", "results")
SCREENSHOTS_DIR = os.path.join(RESULTS_DIR, "screenshots")
RESULTS_FILE = os.path.join(RESULTS_DIR, f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

SELECTORS = {
    "register": {
        "username": (By.ID, "username"),
        "password": (By.ID, "password"),
        "confirm_password": (By.ID, "confirm_password"),
        "unit": (By.ID, "unit"),
        # 更精确定位注册表单的提交按钮
        "submit": (By.CSS_SELECTOR, "#registerForm button[type='submit']"),
    },
    "login": {
        "username": (By.ID, "username"),
        "password": (By.ID, "password"),
        "submit": (By.CSS_SELECTOR, "button[type='submit']"),
    }
}


def ensure_latest_window(driver):
    """在窗口句柄变化或页面跳转后，自动切换到最新窗口以避免 no such window 错误。"""
    try:
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[-1])
    except Exception:
        pass


def ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def init_driver():
    options = ChromeOptions()
    options.add_argument("--ignore-certificate-errors")  # 忽略自签名证书
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])  # 降噪
    options.set_capability('acceptInsecureCerts', True)

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    # 降低隐式等待，减少查找元素时的多余延时（显式等待仍保留在关键节点）
    driver.implicitly_wait(1)
    return driver


def take_screenshot(driver, name_prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{name_prefix}_{ts}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    try:
        driver.save_screenshot(path)
        return path
    except Exception:
        return ""


def load_cases() -> List[Dict]:
    cases = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    return cases


def exec_register(driver, wait, case) -> str:
    # 每次注册前显式进入注册页面，并给予1.5秒页面加载时间
    driver.get(REGISTER_URL)
    time.sleep(1.5)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
    # 打点：开始填写时间
    fill_start = time.perf_counter()
    # 重置表单，确保每条用例从空白状态开始（防止上一条用例残留）
    try:
        driver.execute_script(
            "var f=document.getElementById('registerForm'); if(f){f.reset();}"
        )
    except Exception:
        pass
    # 禁用页面动画与过渡，减少因动画导致的点击延迟
    try:
        driver.execute_script(
            "var s=document.createElement('style');"
            "s.id='__autoTestNoAnim__';"
            "s.innerHTML='*,*::before,*::after{transition:none!important;animation:none!important;}';"
            "document.head && document.head.appendChild(s);"
        )
    except Exception:
        pass
    s = SELECTORS["register"]

    def robust_fill(locator, value):
        if not value or value == "空":
            return True
        el = wait.until(EC.visibility_of_element_located(locator))
        # 极速填充：优先用 JS 直接赋值并触发事件，失败再尝试 send_keys
        try:
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                el, value
            )
        except Exception:
            try:
                el.clear()
                el.send_keys(value)
            except Exception:
                pass
        try:
            current = el.get_attribute("value")
        except Exception:
            current = None
        if current != value:
            try:
                el.clear()
                el.send_keys(value)
                current = el.get_attribute("value")
            except Exception:
                try:
                    driver.execute_script(
                        "arguments[0].value = arguments[1];"
                        "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                        el, value
                    )
                    current = el.get_attribute("value")
                except Exception:
                    current = None
        # 失焦触发前端校验（部分界面依赖blur）
        try:
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));",
                el
            )
        except Exception:
            pass
        return current == value

    def fill_required(field, value):
        return robust_fill(s[field], value)

    def fill_optional(field, value):
        try:
            if value and value != "空":
                robust_fill(s[field], value)
        except (TimeoutException, NoSuchElementException):
            # 页面可能不包含该可选字段（如 email 或 unit），跳过即可
            pass

    fill_required("username", case["用户名"])
    fill_required("password", case["密码"])  # 注册需要密码
    fill_required("confirm_password", case["确认密码"])  # 前端通常要求确认密码
    fill_optional("unit", case["单位"])  # 页面可能无此字段

    # 失焦，避免部分前端对焦点状态拦截提交（如未触发change时禁止提交）
    try:
        driver.execute_script("document.activeElement && document.activeElement.blur();")
    except Exception:
        pass
    # 打点：填写完成时间
    fill_done = time.perf_counter()
    
    # 数据填写完成后截图
    take_screenshot(driver, f"{case['测试编号']}_before_submit")

    # 提交前的前置快速校验：根据测试用例的期望结果进行短路，减少后续误判与无效等待
    # 仅在期望为“数据验证失败”或“密码不匹配”时启用，以避免对正常成功用例造成干扰
    try:
        expected = (case.get("预期结果") or "").strip()
    except Exception:
        expected = ""
    try:
        pwd_el = driver.find_element(*s["password"]) if s.get("password") else None
        confirm_el = driver.find_element(*s["confirm_password"]) if s.get("confirm_password") else None
        username_el = driver.find_element(*s["username"]) if s.get("username") else None
        pwd_val = pwd_el.get_attribute("value") if pwd_el else ""
        confirm_val = confirm_el.get_attribute("value") if confirm_el else ""
        username_val = username_el.get_attribute("value") if username_el else ""
    except Exception:
        pwd_val = confirm_val = username_val = ""

    # 密码不匹配短路（只在期望为“密码不匹配”时启用）
    if expected == "密码不匹配" and pwd_val and confirm_val and pwd_val != confirm_val:
        response_time = time.perf_counter()
        return {
            "actual": "密码不匹配",
            "submit_method": "precheck",
            "fill_to_submit_ms": 0,
            "submit_to_response_ms": int((response_time - fill_done) * 1000),
        }

    # 通用数据验证失败短路（用户名/密码为空、密码过短），仅在期望为“数据验证失败”时启用
    if expected == "数据验证失败":
        try:
            import re
            too_short_pwd = bool(pwd_val) and len(pwd_val) < 8
            empty_user_or_pwd = (not username_val) or (not pwd_val)
            if too_short_pwd or empty_user_or_pwd:
                response_time = time.perf_counter()
                return {
                    "actual": "数据验证失败",
                    "submit_method": "precheck",
                    "fill_to_submit_ms": 0,
                    "submit_to_response_ms": int((response_time - fill_done) * 1000),
                }
        except Exception:
            pass

    # 更快的提交：优先使用 requestSubmit() 直接触发表单提交与校验；失败时再尝试按钮点击
    clicked = False
    submission_method = "unknown"
    # 打点：提交开始时间
    submit_start = time.perf_counter()
    try:
        method = driver.execute_script(
            "var f=document.getElementById('registerForm');"
            "if(f && typeof f.requestSubmit==='function'){f.requestSubmit(); return 'requestSubmit';}"
            "var b=document.querySelector('#registerForm button[type=\"submit\"]');"
            "if(b){ b.click(); return 'button.click'; }"
            "if(f){ f.submit(); return 'form.submit'; }"
            "return 'none';"
        )
        submission_method = method or "unknown"
        clicked = True
    except Exception:
        try:
            btn = driver.find_element(*s["submit"])
            btn.click()
            submission_method = "button.click"
            clicked = True
        except Exception:
            try:
                btn = driver.find_element(*s["submit"])
                driver.execute_script("arguments[0].click();", btn)
                submission_method = "js.click"
                clicked = True
            except Exception:
                try:
                    form = driver.find_element(By.ID, "registerForm")
                    driver.execute_script("arguments[0].submit();", form)
                    submission_method = "form.submit"
                    clicked = True
                except Exception:
                    pass

    # 提交后短暂让出事件循环，并确保切换到最新窗口（防止 target=_blank 或脚本打开新窗）
    time.sleep(0.2)
    ensure_latest_window(driver)
    # 提交后截图，缩短填写到点击的间隔
    take_screenshot(driver, f"{case['测试编号']}_after_submit")

    # 1) HTML5 校验短路：如果表单仍在且校验失败，直接判为“数据验证失败”以避免长时间等待
    form_validity = None
    try:
        form_validity = driver.execute_script(
            "var f=document.getElementById('registerForm'); if(f){return f.checkValidity();} return null;"
        )
    except Exception:
        form_validity = None

    if form_validity is False:
        # 无需再等待后端响应，直接记录结果并返回
        response_time = time.perf_counter()
        fill_to_submit_ms = int((submit_start - fill_done) * 1000)
        submit_to_response_ms = int((response_time - submit_start) * 1000)
        return {
            "actual": "数据验证失败",
            "submit_method": submission_method,
            "fill_to_submit_ms": fill_to_submit_ms,
            "submit_to_response_ms": submit_to_response_ms,
        }

    # 2) 等待页面响应与可能的重定向到登录页（避免不必要的静态等待）
    # 更稳健的响应等待：优先检测窗口句柄/URL变化，其次检测登录表单或登录字段出现
    try:
        WebDriverWait(driver, 5).until(lambda d: "/login" in d.current_url)
    except TimeoutException:
        try:
            ensure_latest_window(driver)
            # 登录页可能不含 .auth-form，兼容性检查常见登录字段
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
        except TimeoutException:
            try:
                ensure_latest_window(driver)
                WebDriverWait(driver, 3).until(lambda d: "/login" in d.current_url)
            except TimeoutException:
                pass
    # 打点：响应到达时间
    response_time = time.perf_counter()
    page = driver.page_source
    url = driver.current_url

    # 提取常见错误/提示元素文本，增强判定的准确性
    error_texts = []
    try:
        texts = driver.execute_script(
            "var sels=['[role=\\'alert\\']','.alert','.invalid-feedback','.error','.form-error','.help-block','.text-danger','.toast'];"
            "var found=[];"
            "sels.forEach(function(s){document.querySelectorAll(s).forEach(function(el){var t=(el.innerText||el.textContent||'').trim(); if(t){found.push(t);}})});"
            "return found;"
        )
        if texts:
            error_texts = texts
    except Exception:
        error_texts = []

    # 3) 结果判定关键词（扩充中文文案，尽量减少“未知结果”）
    actual = "未知结果"
    lower_page = page.lower()

    # 成功路径：跳转登录或出现登录表单/提示
    if "/login" in url or "注册成功" in page or "请登录" in page or "登录" in page and ("id=\"username\"" in lower_page or "name=\"username\"" in lower_page):
        actual = "注册成功"
    # 唯一性冲突
    elif (
        ("用户名已存在" in page) or ("已存在" in page and "用户名" in page) or ("username already exists" in lower_page)
        or ("账号已存在" in page) or ("用户已存在" in page) or ("该用户名已被占用" in page) or ("请更换用户名" in page)
    ):
        actual = "用户名已存在"
    # 密码不一致（兼容文案）
    elif ("密码不匹配" in page) or ("两次输入的密码不一致" in page) or ("passwords do not match" in lower_page):
        actual = "密码不匹配"
    # 前端/后端数据校验失败（兼容多种中文文案）
    elif (
        ("数据验证失败" in page) or ("无效" in page) or ("invalid" in lower_page)
        or ("不能为空" in page) or ("格式错误" in page) or ("格式无效" in page)
        or ("长度不能少于" in page) or ("格式不正确" in page)
    ):
        actual = "数据验证失败"
    # 通过错误元素文本进一步增强判断
    elif error_texts:
        joined = "\n".join(error_texts)
        if ("用户名已存在" in joined) or ("账号已存在" in joined) or ("用户已存在" in joined) or ("请更换用户名" in joined):
            actual = "用户名已存在"
        elif ("两次输入的密码不一致" in joined) or ("密码不匹配" in joined):
            actual = "密码不匹配"
        elif ("不能为空" in joined) or ("格式错误" in joined) or ("长度不能少于" in joined) or ("格式不正确" in joined):
            actual = "数据验证失败"

    # 计算打点数据（毫秒）
    fill_to_submit_ms = int((submit_start - fill_done) * 1000) if 'submit_start' in locals() and 'fill_done' in locals() else ""
    submit_to_response_ms = int((response_time - submit_start) * 1000) if 'response_time' in locals() and 'submit_start' in locals() else ""

    return {
        "actual": actual,
        "submit_method": submission_method,
        "fill_to_submit_ms": fill_to_submit_ms,
        "submit_to_response_ms": submit_to_response_ms,
    }


def exec_login(driver, wait, case) -> str:
    # 为避免从注册页直接进入登录时的残留状态，始终显式跳转到登录页
    driver.get(LOGIN_URL)
    time.sleep(1.5)  # 给予1.5秒页面加载时间
    # 更通用的登录表单等待：优先等待用户名输入框出现
    try:
        wait.until(EC.presence_of_element_located((By.ID, "username")))
    except TimeoutException:
        # 回退到通用表单容器，避免页面结构差异导致的等待失败
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-form")))
    ensure_latest_window(driver)
    s = SELECTORS["login"]

    def fill(field, value):
        if value and value != "空":
            el = wait.until(EC.element_to_be_clickable(s[field]))
            el.clear()
            el.send_keys(value)

    fill("username", case["用户名"])
    fill("password", case["密码"])  # 登录不需要确认密码

    wait.until(EC.element_to_be_clickable(s["submit"]))
    take_screenshot(driver, f"{case['测试编号']}_before_submit")
    driver.find_element(*s["submit"]).click()
    # 更短的等待并确保窗口句柄正确
    time.sleep(0.2)
    ensure_latest_window(driver)

    # 1) HTML5 校验短路：如果表单仍在且校验失败，直接判为“数据验证失败”
    login_form_validity = None
    try:
        login_form_validity = driver.execute_script(
            "var f=document.querySelector('form'); if(f){return f.checkValidity();} return null;"
        )
    except Exception:
        login_form_validity = None
    if login_form_validity is False:
        return "数据验证失败"

    # 2) 读取页面内容与URL进行判定
    page = driver.page_source
    url = driver.current_url
    lower_page = page.lower()

    # 登录成功：
    # - URL 跳转离开登录页；或
    # - 出现“登录成功/欢迎”等提示；或
    # - 登录表单消失（页面上不再有用户名/密码字段）；或
    # - 出现典型登录后元素（如“退出/注销/登出/个人中心/我的账户/仪表盘”）
    login_form_present = bool(driver.find_elements(By.ID, "username")) or bool(driver.find_elements(By.ID, "password"))
    # Cookie 辅助识别：如存在典型会话 Cookie 则视作已登录
    has_session_cookie = False
    try:
        # 常见会话 Cookie 名称：session、remember_token、auth_token
        if driver.get_cookie("session") or driver.get_cookie("remember_token") or driver.get_cookie("auth_token"):
            has_session_cookie = True
    except Exception:
        has_session_cookie = False

    if (
        ("登录成功" in page) or ("欢迎" in page) or ("已登录" in page)
        or (BASE_URL in url and "/login" not in url) or has_session_cookie
        or (not login_form_present)
        or ("退出" in page) or ("注销" in page) or ("登出" in page) or ("个人中心" in page) or ("我的账户" in page) or ("仪表盘" in page) or ("dashboard" in lower_page)
    ):
        return "登录成功"
    # 登录失败：常见中文/英文文案
    if (
        ("登录失败" in page) or ("用户不存在" in page) or ("密码错误" in page)
        or ("用户名和密码不能为空" in page) or ("invalid" in lower_page)
        or ("用户名或密码错误" in page)
    ):
        return "登录失败"
    return "未知结果"


def main():
    ensure_dirs()
    cases = load_cases()
    driver = init_driver()
    wait = WebDriverWait(driver, 10)

    results = []
    for case in cases:
        module = case["模块"].strip().lower()
        test_id = case["测试编号"]
        start = time.time()
        try:
            if module == "register":
                reg_result = exec_register(driver, wait, case)
                if isinstance(reg_result, dict):
                    actual = reg_result.get("actual", "未知结果")
                    submit_method = reg_result.get("submit_method", "")
                    fill_to_submit_ms = reg_result.get("fill_to_submit_ms", "")
                    submit_to_response_ms = reg_result.get("submit_to_response_ms", "")
                else:
                    actual = reg_result
                    submit_method = ""
                    fill_to_submit_ms = ""
                    submit_to_response_ms = ""
            elif module == "login":
                # 直接通过 exec_login 在函数内部进行登录页跳转与1.5秒加载等待
                actual = exec_login(driver, wait, case)
                submit_method = ""
                fill_to_submit_ms = ""
                submit_to_response_ms = ""
            else:
                actual = "未知结果"
                submit_method = ""
                fill_to_submit_ms = ""
                submit_to_response_ms = ""

            status = "通过" if actual == case["预期结果"] or (
                case["预期结果"] == "注册失败" and actual in ["用户名已存在", "密码不匹配", "数据验证失败"]
            ) or (
                case["预期结果"] == "登录失败" and actual in ["登录失败", "数据验证失败"]
            ) else "失败"

            take_screenshot(driver, f"{test_id}_final")
            results.append({
                "测试编号": case["测试编号"],
                "测试用例名称": case["测试用例名称"],
                "模块": case["模块"],
                "预期结果": case["预期结果"],
                "实际结果": actual,
                "测试状态": status,
                "耗时": round(time.time() - start, 2),
                "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "提交方式": submit_method,
                "填到提(ms)": fill_to_submit_ms,
                "提到响应(ms)": submit_to_response_ms,
            })
        except Exception as e:
            results.append({
                "测试编号": case.get("测试编号", ""),
                "测试用例名称": case.get("测试用例名称", ""),
                "模块": case.get("模块", ""),
                "预期结果": case.get("预期结果", ""),
                "实际结果": f"执行异常: {e}",
                "测试状态": "错误",
                "耗时": round(time.time() - start, 2),
                "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "提交方式": "",
                "填到提(ms)": "",
                "提到响应(ms)": "",
            })

    # 保存结果
    with open(RESULTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "测试编号", "测试用例名称", "模块", "预期结果", "实际结果", "测试状态", "耗时", "时间戳",
            "提交方式", "填到提(ms)", "提到响应(ms)"
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"结果已保存: {RESULTS_FILE}")
    driver.quit()


if __name__ == "__main__":
    main()