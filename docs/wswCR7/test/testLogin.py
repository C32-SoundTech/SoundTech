import unittest
from unittest.mock import patch, MagicMock
from flask import session
import app  
from werkzeug.security import generate_password_hash

class TestLogin(unittest.TestCase):
    
       
    def setUp(self): # 配置测试环境
        self.app = app.app.test_client()
        self.app.testing = True
        app.app.config['SECRET_KEY'] = 'test_secret_key'
        
    def test_login_page_loads(self):# 测试登录页面是否正常加载
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('登录', response.data.decode('utf-8'))
        
    @patch('app.login_util')
    def test_successful_login(self, mock_login_util):# 测试正常登录流程
        # 模拟login_util返回用户信息
        mock_user = {
            'id': 1,
            'username': 'testuser',
            'password_hash': generate_password_hash('password123')
        }
        mock_login_util.return_value = mock_user
        
        with self.app as client:
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            # 验证是否调用了login_util函数
            mock_login_util.assert_called_once_with('testuser')
            
            # 验证是否设置了会话
            self.assertEqual(session['user_id'], 1)
            
            # 验证是否重定向到主页
            self.assertIn('首页', response.data.decode('utf-8'))
        
    def test_empty_username(self):# 测试空用户名
        response = self.app.post('/login', data={
            'username': '',
            'password': 'password123'
        })
        self.assertIn('用户名和密码不能为空', response.data.decode('utf-8'))
        
    def test_empty_password(self):# 测试空密码
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': ''
        })
        self.assertIn('用户名和密码不能为空', response.data.decode('utf-8'))
        
    @patch('app.login_util')
    def test_wrong_password(self, mock_login_util):# 测试密码错误
        # 模拟login_util返回用户信息
        mock_user = {
            'id': 1,
            'username': 'testuser',
            'password_hash': generate_password_hash('correctpassword')
        }
        mock_login_util.return_value = mock_user
        
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertIn('登录失败，用户名或密码错误', response.data.decode('utf-8'))
        
    @patch('app.login_util')
    def test_nonexistent_user(self, mock_login_util):# 测试用户不存在
        # 模拟login_util返回None表示用户不存在
        mock_login_util.return_value = None
        
        response = self.app.post('/login', data={
            'username': 'nonexistentuser',
            'password': 'password123'
        })
        self.assertIn('登录失败，用户名或密码错误', response.data.decode('utf-8'))
        
    @patch('app.login_util')
    def test_redirect_with_next_param(self, mock_login_util):# 测试带next参数的重定向
        # 模拟login_util返回用户信息
        mock_user = {
            'id': 1,
            'username': 'testuser',
            'password_hash': generate_password_hash('password123')
        }
        mock_login_util.return_value = mock_user
        
        with self.app as client:
            response = client.post('/login?next=/profile', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=False)
            
            # 验证是否重定向到next参数指定的页面
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith('/profile'))

if __name__ == '__main__':
    unittest.main()