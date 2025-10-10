import unittest
from unittest.mock import patch, MagicMock
from flask import session
import app  # 导入主应用
from werkzeug.security import generate_password_hash

class TestRegister(unittest.TestCase):
    
    def setUp(self):
        self.app = app.app.test_client()
        self.app.testing = True
        
    def test_register_page_loads(self):# 测试注册页面是否正常加载
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn('注册', response.data.decode('utf-8'))
        
    @patch('app.register_util')
    def test_successful_registration(self, mock_register_util):# 测试正常注册流程
        # 模拟register_util返回True表示注册成功
        mock_register_util.return_value = True
        
        response = self.app.post('/register', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        # 验证是否调用了register_util函数
        mock_register_util.assert_called_once_with('testuser', 'password123')
        
        # 验证是否重定向到登录页面
        self.assertIn('登录', response.data.decode('utf-8'))
        self.assertIn('注册成功', response.data.decode('utf-8'))
        
    def test_empty_username_password(self):# 测试空用户名或密码
        # 测试空用户名
        response = self.app.post('/register', data={
            'username': '',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertIn('用户名和密码不能为空', response.data.decode('utf-8'))
        
        # 测试空密码
        response = self.app.post('/register', data={
            'username': 'testuser',
            'password': '',
            'confirm_password': ''
        })
        self.assertIn('用户名和密码不能为空', response.data.decode('utf-8'))
        
    def test_password_mismatch(self):# 测试密码不匹配
        response = self.app.post('/register', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password456'
        })
        self.assertIn('两次输入的密码不一致', response.data.decode('utf-8'))
        
    def test_password_too_short(self):# 测试密码长度不足
        response = self.app.post('/register', data={
            'username': 'testuser',
            'password': '12345',
            'confirm_password': '12345'
        })
        self.assertIn('密码长度不能少于6个字符', response.data.decode('utf-8'))
        
    @patch('app.register_util')
    def test_username_already_exists(self, mock_register_util):# 测试用户名已存在
        # 模拟register_util返回False表示用户名已存在
        mock_register_util.return_value = False
        
        response = self.app.post('/register', data={
            'username': 'existinguser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        self.assertIn('用户名已存在', response.data.decode('utf-8'))
        
    @patch('app.register_util')
    def test_register_util_integration(self, mock_register_util):# 测试register_util函数集成
        # 模拟数据库操作
        def side_effect(username, password):
            if username == 'existinguser':
                return False
            return True
            
        mock_register_util.side_effect = side_effect
        
        # 测试新用户注册
        response = self.app.post('/register', data={
            'username': 'newuser',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn('注册成功', response.data.decode('utf-8'))
        
        # 测试已存在用户注册
        response = self.app.post('/register', data={
            'username': 'existinguser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertIn('用户名已存在', response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()