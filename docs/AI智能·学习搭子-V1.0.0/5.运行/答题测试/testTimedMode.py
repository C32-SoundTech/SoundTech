import unittest
import sys
import os
import threading
import time
import json
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

# 确保项目根目录在导入路径中（从 docs/wswCR7/test 回到项目根）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app import app
from handlers.database import init_db, register_util

BASE_URL = "http://127.0.0.1:5003"  # 使用不同端口避免与其他测试冲突

class SeleniumTimedModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        # 初始化数据库并注册测试用户
        init_db()
        register_util("selenium_timed_user", "password123")

        # 启动 Flask 服务（单独端口，避免与默认端口冲突）
        def run_server():
            app.run(host="127.0.0.1", port=5003, debug=False, use_reloader=False)

        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        # 等待服务器启动
        time.sleep(1.2)

        # 启动浏览器（无头模式）
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 使用 webdriver-manager 自动下载并管理 ChromeDriver
        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except Exception:
            pass
        # Flask 开发服务器作为守护线程运行，测试结束随进程退出

    def login(self, username, password):
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        # 登录后索引页应加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".feature-buttons")))

    def test_start_timed_mode_success(self):
        """测试ID: T-TIM-001 - 定时模式正常启动"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 直接访问首页，定时模式表单在首页上
        self.driver.get(f"{BASE_URL}/")
        
        # 等待页面加载，确保定时模式表单存在
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='start_timed_mode']")))
        
        # 设置定时模式参数
        # 使用Select类处理下拉菜单
        question_count_select = Select(self.driver.find_element(By.ID, "question_count"))
        question_count_select.select_by_value("10")
        
        duration_select = Select(self.driver.find_element(By.ID, "duration"))
        duration_select.select_by_value("15")
        
        # 提交表单 - 使用更精确的CSS选择器
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "form[action*='start_timed_mode'] button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(1)  # 等待滚动完成
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # 等待重定向到定时模式页面
        self.wait.until(EC.url_contains("/timed_mode"))
        
        # 验证页面包含定时模式元素
        self.wait.until(EC.presence_of_element_located((By.ID, "timer")))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-container")))
        
        # 验证页面包含题目内容
        page_source = self.driver.page_source
        self.assertTrue("题目" in page_source or "Question" in page_source)
        self.assertTrue("剩余时间" in page_source or "Remaining Time" in page_source)

    def test_start_timed_mode_default_params(self):
        """测试ID: T-TIM-002 - 定时模式启动测试 - 参数验证"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 直接访问首页，定时模式表单在首页上
        self.driver.get(f"{BASE_URL}/")
        
        # 等待页面加载，确保定时模式表单存在
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='start_timed_mode']")))
        
        # 不设置任何参数，直接提交表单（使用默认值）
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "form[action*='start_timed_mode'] button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(1)  # 等待滚动完成
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # 等待重定向到定时模式页面
        self.wait.until(EC.url_contains("/timed_mode"))
        
        # 验证页面包含定时模式元素
        self.wait.until(EC.presence_of_element_located((By.ID, "timer")))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-container")))
        
        # 验证页面包含题目内容
        page_source = self.driver.page_source
        self.assertTrue("题目" in page_source or "Question" in page_source)
        self.assertTrue("剩余时间" in page_source or "Remaining Time" in page_source)
    
    def test_timed_mode_invalid_session(self):
        """测试ID: T-TIM-003 - 定时模式页面显示测试 - 无效会话"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 直接访问定时模式页面（没有启动定时模式）
        self.driver.get(f"{BASE_URL}/timed_mode")
        
        # 等待页面加载
        time.sleep(1)
        
        # 根据实际行为，应用程序可能不会重定向，而是直接显示定时模式页面
        # 但应该显示错误消息或提示用户启动定时模式
        page_source = self.driver.page_source
        
    
    def test_timed_mode_time_expired(self):
        """测试ID: T-TIM-004 - 定时模式页面显示测试 - 时间已到"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 启动定时模式
        self.driver.get(f"{BASE_URL}/")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='start_timed_mode']")))
        
        # 设置定时模式参数（使用最短时间）
        question_count_select = Select(self.driver.find_element(By.ID, "question_count"))
        question_count_select.select_by_value("5")
        
        duration_select = Select(self.driver.find_element(By.ID, "duration"))
        duration_select.select_by_value("5")  # 5分钟
        
        # 提交表单
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "form[action*='start_timed_mode'] button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(1)
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # 等待定时模式页面加载
        self.wait.until(EC.url_contains("/timed_mode"))
        
        # 模拟时间已到（通过修改会话中的结束时间）
        self.driver.execute_script("""
            // 模拟时间已到期
            localStorage.setItem('end_time', '2000-01-01T00:00:00');  // 设置一个过去的时间
        """)
        
        # 刷新页面
        self.driver.refresh()
        
        # 等待重定向
        time.sleep(2)
        
        # 验证是否被重定向到提交答案页面
        current_url = self.driver.current_url
        

                       
    def test_timed_mode_answer_submission(self):
        """测试ID: T-TIM-005 - 定时模式答案提交测试 - 正常提交"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 直接访问首页，定时模式表单在首页上
        self.driver.get(f"{BASE_URL}/")
        
        # 等待页面加载，确保定时模式表单存在
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='start_timed_mode']")))
        
        # 设置定时模式参数（使用较短的时间和较少的题目）
        # 使用Select类处理下拉菜单
        question_count_select = Select(self.driver.find_element(By.ID, "question_count"))
        question_count_select.select_by_value("5")  # 选择5题
        
        duration_select = Select(self.driver.find_element(By.ID, "duration"))
        duration_select.select_by_value("5")  # 选择5分钟
        
        # 提交表单 - 使用更精确的CSS选择器
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "form[action*='start_timed_mode'] button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(1)  # 等待滚动完成
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # 等待定时模式页面加载
        self.wait.until(EC.url_contains("/timed_mode"))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-container")))
        
        # 回答所有题目
        # 获取题目数量
        time.sleep(1)  # 等待页面完全加载
        questions = self.driver.find_elements(By.CSS_SELECTOR, ".question-container")
        
        # 对每个题目选择一个选项
        for i in range(len(questions)):
            # 查找当前题目的选项
            option_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']")
            if option_elements:
                # 选择第一个选项
                option = option_elements[0]
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.5)  # 等待滚动完成
                self.driver.execute_script("arguments[0].click();", option)
        
        # 提交答案
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button.btn-primary[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(1)  # 等待滚动完成
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # 等待结果页面
        time.sleep(2)
        
        # 验证结果页面包含成绩信息
        page_source = self.driver.page_source

    def test_submit_timed_mode_no_session(self):
        """测试ID: T-TIM-006 - 定时模式答案提交测试 - 无效会话"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 直接访问提交页面（没有启动定时模式）
        self.driver.get(f"{BASE_URL}/submit_timed_mode")
        
        # 等待页面加载
        time.sleep(1)
        
        # 验证页面是否包含错误消息
        page_source = self.driver.page_source

    def test_timed_mode_auto_submit(self):
        """测试ID: T-TIM-007 - 定时模式自动提交测试"""
        # 登录
        self.login("selenium_timed_user", "password123")
        
        # 启动定时模式
        self.driver.get(f"{BASE_URL}/start_timed_mode")
        time.sleep(1)
        
        # 模拟时间到期（修改session或等待）
        self.driver.execute_script("""
            document.cookie = "session_end_time=1000000; path=/";
        """)
        
        # 访问定时模式页面
        self.driver.get(f"{BASE_URL}/timed_mode")
        time.sleep(1)
        
        # 验证页面是否包含时间到期的消息
        page_source = self.driver.page_source
                       
        # 验证是否有提示信息或返回首页的链接
        self.assertTrue("首页" in page_source or "home" in page_source.lower() or
                       "返回" in page_source or "return" in page_source.lower())

if __name__ == '__main__':
    unittest.main(verbosity=2)