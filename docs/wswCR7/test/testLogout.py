import unittest
from flask import session
import app  # 导入主应用

class TestLogout(unittest.TestCase):
    """测试用户登出功能"""
    
    def setUp(self):# 配置测试环境
        self.app = app.app.test_client()
        self.app.testing = True
        app.app.config['SECRET_KEY'] = 'test_secret_key'
        
    def test_normal_logout(self):# 测试正常登出流程
        with self.app as client:
            with client.session_transaction() as sess:
                # 模拟用户已登录
                sess['user_id'] = 1
            
            # 访问登出路由
            response = client.get('/logout', follow_redirects=True)
            
            # 验证会话是否被清除
            self.assertNotIn('user_id', session)
            
            # 验证是否重定向到登录页面
            self.assertEqual(response.status_code, 200)
            self.assertIn('登录', response.data.decode('utf-8'))
            
            # 验证是否显示成功登出消息
            self.assertIn('您已成功退出登录', response.data.decode('utf-8'))
    
    def test_logout_when_not_logged_in(self):# 测试未登录状态下的登出
        with self.app as client:
            # 确保没有登录
            with client.session_transaction() as sess:
                if 'user_id' in sess:
                    del sess['user_id']
            
            # 访问登出路由
            response = client.get('/logout', follow_redirects=True)
            
            # 验证是否重定向到登录页面
            self.assertEqual(response.status_code, 200)
            self.assertIn('登录', response.data.decode('utf-8'))
    
    def test_session_state_after_logout(self):# 测试登出后会话状态
        with self.app as client:
            # 模拟用户已登录并设置多个会话变量
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
                sess['test_data'] = 'some_data'
            
            # 访问登出路由
            client.get('/logout')
            
            # 验证所有会话变量是否被清除
            self.assertEqual(session, {})
            
            # 尝试访问需要登录的页面（假设/favorites需要登录）
            response = client.get('/favorites', follow_redirects=True)
            
            # 验证是否被重定向到登录页面
            self.assertIn('登录', response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()