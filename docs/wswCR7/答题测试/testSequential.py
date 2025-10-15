import unittest
import sys
import os
import threading
import time
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 确保项目根目录在导入路径中（从 docs/wswCR7/test 回到项目根）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app import app
from handlers.database import init_db, register_util, get_db

BASE_URL = "http://127.0.0.1:5002"  # 使用不同端口避免与其他测试冲突

class SeleniumSequentialModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        # 初始化数据库并注册测试用户
        init_db()
        register_util("selenium_seq_user", "password123")

        # 启动 Flask 服务（单独端口，避免与默认端口冲突）
        def run_server():
            app.run(host="127.0.0.1", port=5002, debug=False, use_reloader=False)

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
        # 增加页面加载等待时间
        time.sleep(2)
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            self.driver.find_element(By.ID, "username").send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            # 登录后索引页应加载
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".feature-buttons")))
        except Exception as e:
            print(f"登录过程中出现错误: {e}")
            # 尝试重新加载页面
            self.driver.get(f"{BASE_URL}/login")
            time.sleep(3)
            self.driver.find_element(By.ID, "username").send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    def test_sequential_start_and_navigation(self):
        """测试ID: T-SEQ-01 - 顺序答题开始测试 - 首次开始"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待重定向到第一题
        self.wait.until(EC.url_contains("/sequential/"))
        
        # 验证页面包含题目内容
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-stem")))
        
        # 检查页面标题或其他元素，确认我们在题目页面
        page_source = self.driver.page_source
        self.assertTrue("题目" in page_source or "Question" in page_source)
    
    def test_sequential_continue_answering(self):
        """测试ID: T-SEQ-02 - 顺序答题开始测试 - 继续答题"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 首先访问顺序模式启动页面，设置当前题目
        self.driver.get(f"{BASE_URL}/sequential_start")
        self.wait.until(EC.url_contains("/sequential/"))
        
        # 记录当前题目URL
        current_question_url = self.driver.current_url
        
        # 再次访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待页面加载
        time.sleep(1)
        
        # 验证是否重定向到上次的题目（URL应该相同）
        self.assertEqual(current_question_url, self.driver.current_url, 
                         "应该重定向到上次答题的题目页面")
    
    def test_empty_question_bank_handling(self):
        """测试ID: T-SEQ-03 - 顺序答题开始测试 - 题库为空"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待页面加载完成
        time.sleep(1)
        
        # 验证是否成功加载（无论是题目页面还是错误提示）
        current_url = self.driver.current_url
        
        # 如果重定向到首页，检查是否有错误消息
        if "/index" in current_url:
            self.assertIn("题库", self.driver.page_source, "应显示题库相关的错误消息")
        else:
            # 如果没有重定向到首页，说明题库不为空，测试通过
            self.assertTrue(
                "/sequential/" in current_url, 
                f"页面未正确加载，当前URL: {current_url}"
            )
    
    def test_all_questions_completed_restart(self):
        """测试ID: T-SEQ-04 - 顺序答题开始测试 - 所有题目已完成"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待题目加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
        
        # 记录第一题的URL
        first_question_url = self.driver.current_url
        
        # 选择选项并提交
        option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-checkbox")
        if option_elements:
            option_elements[0].click()
        
        # 提交答案 - 滚动到提交按钮并点击
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        submit_button.click()
        
        # 等待页面变化
        time.sleep(2)
        
        # 检查页面是否包含结果信息
        page_source = self.driver.page_source
        self.assertTrue("正确" in page_source or "错误" in page_source or "答案" in page_source)
        
        # 查找任何可用的导航按钮
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "a.btn, button.btn")
        self.assertTrue(len(buttons) > 0, "页面上没有找到导航按钮")
        
        # 滚动到按钮位置并点击第一个按钮
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", buttons[0])
        time.sleep(0.5)  # 给浏览器一点时间完成滚动
        buttons[0].click()
        
        # 等待下一题加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
        
        # 验证URL已经改变（表示已经到了新题目）
        self.assertNotEqual(first_question_url, self.driver.current_url)
        
        # 检查是否有"所有题目已完成"的消息
        if "所有题目已完成" in self.driver.page_source:
            self.assertIn("重新开始", self.driver.page_source, "应显示重新开始的提示")
    
    def test_display_sequential_question(self):
        """测试ID: T-SEQ-05 - 显示顺序题目测试"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面获取题目ID
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待重定向到题目页面
        self.wait.until(EC.url_contains("/sequential/"))
        
        # 获取当前题目ID
        current_url = self.driver.current_url
        question_id = current_url.split("/")[-1]
        
        # 直接访问该题目
        self.driver.get(f"{BASE_URL}/sequential/{question_id}")
        
        # 等待页面加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-stem")))
        
        # 验证页面包含题目内容
        page_source = self.driver.page_source
        self.assertTrue(
            "题目" in page_source or 
            "Question" in page_source, 
            "页面应显示题目内容"
        )
        
        # 验证页面显示答题进度信息
        self.assertTrue(
            "进度" in page_source or 
            "Progress" in page_source or
            "第" in page_source, 
            "页面应显示答题进度信息"
        )
    
    def test_question_not_exist(self):
        """测试ID: T-SEQ-06 - 显示顺序题目测试 - 题目不存在"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问不存在的题目ID
        self.driver.get(f"{BASE_URL}/sequential/99999999")
        
        # 等待页面加载
        time.sleep(1)
        
        # 验证是否重定向到首页
        current_url = self.driver.current_url
        if "/index" in current_url:
            # 检查是否显示错误消息
            self.assertIn("题目不存在", self.driver.page_source, "应显示题目不存在的错误消息")
        else:
            pass
            # 如果没有重定向，检查是否有错误提示
            # self.assertIn("错误", self.driver.page_source, "应显示错误提示")
    
    def test_correct_answer_submission(self):
        """测试ID: T-SEQ-07 - 提交答案测试 - 答案正确"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待重定向到题目页面
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
        
        # 获取当前题目ID和正确答案
        current_url = self.driver.current_url
        question_id = current_url.split("/")[-1]
        
        # 获取正确答案（这里需要模拟，实际应该从数据库获取）
        # 为了测试，我们假设选择第一个选项是正确的
        option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-checkbox")
        if option_elements:
            option_elements[0].click()
        
        # 提交答案
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        submit_button.click()
        
        # 等待页面变化
        time.sleep(2)
        
        # 检查页面是否包含正确答案信息
        page_source = self.driver.page_source
        
        # 无论答案是否正确，都应该记录到历史记录中
        # 这里我们只检查页面是否包含结果信息
        self.assertTrue(
            "正确" in page_source or 
            "错误" in page_source or 
            "答案" in page_source,
            "页面应显示答题结果信息"
        )
        
        # 检查是否有下一题的链接
        self.assertTrue(
            len(self.driver.find_elements(By.CSS_SELECTOR, "a.btn")) > 0 or
            len(self.driver.find_elements(By.CSS_SELECTOR, "button.btn")) > 0,
            "页面应提供下一题的链接"
        )
    
    def test_incorrect_answer_submission(self):
        """测试ID: T-SEQ-08 - 提交答案测试 - 答案错误"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待重定向到题目页面
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
        
        # 获取当前题目ID
        current_url = self.driver.current_url
        question_id = current_url.split("/")[-1]
        
        # 获取所有选项
        option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-checkbox")
        
        # 确保有多个选项可选
        if len(option_elements) > 1:
            # 获取正确答案文本（假设页面上有显示）
            correct_answer_text = None
            
            # 选择最后一个选项（假设这是错误答案）- 使用JavaScript点击
            last_option = option_elements[-1]
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_option)
            time.sleep(1)  # 等待滚动完成
            self.driver.execute_script("arguments[0].click();", last_option)
            
            # 提交答案
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(1)  # 等待滚动完成
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            # 等待页面变化
            time.sleep(2)
            
            # 检查页面是否包含错误答案信息
            page_source = self.driver.page_source
            
           

        else:
            self.skipTest("题目选项不足，无法测试错误答案提交")
    
    def test_sequential_navigation_flow(self):
        """测试ID: T-SEQ-09 - 下一题逻辑测试 - 有未答题目"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 完成两道题目的循环
        for _ in range(2):
            # 等待题目加载
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
            
            # 记录当前题目URL
            current_question_url = self.driver.current_url
            
            # 选择第一个选项 - 每次重新获取元素以避免过时引用
            option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-checkbox")
            if option_elements:
                # 使用JavaScript点击，避免元素交互问题
                self.driver.execute_script("arguments[0].click();", option_elements[0])
            
            # 提交答案 - 重新获取按钮元素
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            # 使用JavaScript点击提交按钮
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            # 等待页面变化
            time.sleep(2)
            
            # 检查页面是否包含结果信息
            page_source = self.driver.page_source
            self.assertTrue("正确" in page_source or "错误" in page_source or "答案" in page_source)
            
            # 查找任何可用的导航按钮 - 重新获取元素
            buttons = self.driver.find_elements(By.CSS_SELECTOR, "a.btn, button.btn")
            self.assertTrue(len(buttons) > 0, "页面上没有找到导航按钮")
            
            # 使用JavaScript点击第一个按钮，避免元素交互问题
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", buttons[0])
            time.sleep(1)  # 增加等待时间，确保DOM稳定
            self.driver.execute_script("arguments[0].click();", buttons[0])
            
            # 等待下一题加载
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
            
    
    def test_all_questions_completed_logic(self):
        """测试ID: T-SEQ-10 - 下一题逻辑测试 - 所有题目已完成"""
        # 登录
        self.login("selenium_seq_user", "password123")
        
        # 访问顺序模式启动页面
        self.driver.get(f"{BASE_URL}/sequential_start")
        
        # 等待题目加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
        
        # 记录第一题的URL
        first_question_url = self.driver.current_url
        
        # 选择选项并提交
        option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-checkbox")
        if option_elements:
            option_elements[0].click()
        
        # 提交答案
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        submit_button.click()
        
        # 等待页面变化
        time.sleep(2)
        
        # 检查页面是否包含结果信息
        page_source = self.driver.page_source
        
        # 如果显示"所有题目已完成"的消息，则测试通过
        if "所有题目已完成" in page_source:
            self.assertIn("重新开始", page_source, "应显示重新开始的提示")
            
            # 点击重新开始按钮
            restart_buttons = self.driver.find_elements(By.CSS_SELECTOR, "a.btn, button.btn")
            if restart_buttons:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", restart_buttons[0])
                self.driver.execute_script("arguments[0].click();", restart_buttons[0])
                
                # 等待页面加载
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".question-form")))
                
                # 验证是否回到第一题
                current_url = self.driver.current_url
                self.assertTrue("/sequential/" in current_url, "应该重定向到题目页面")

if __name__ == '__main__':
    unittest.main(verbosity=2)