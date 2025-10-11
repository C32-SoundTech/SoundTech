import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from handlers.database import search_util

class TestSearchFunction(unittest.TestCase):
    """测试搜索题目功能的单元测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.app = app.test_client()
        self.app.testing = True
        # 创建测试会话
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1  # 模拟已登录用户
    
    @patch('app.search_util')
    def test_search_empty_query(self, mock_search_util):
        """测试空查询"""
        response = self.app.post('/search', data={'query': ''})
        self.assertEqual(response.status_code, 200)
        mock_search_util.assert_not_called()
    
    @patch('app.search_util')
    def test_search_with_query(self, mock_search_util):
        """测试有效查询"""
        # 模拟搜索结果
        mock_search_util.return_value = [
            {'id': '1', 'stem': '测试题目1'},
            {'id': '2', 'stem': '测试题目2'}
        ]
        
        response = self.app.post('/search', data={'query': '测试'})
        self.assertEqual(response.status_code, 200)
        mock_search_util.assert_called_once_with('测试')
        
        # 检查返回的HTML是否包含搜索结果
        html = response.data.decode('utf-8')
        self.assertIn('测试题目1', html)
        self.assertIn('测试题目2', html)
    
    @patch('app.search_util')
    def test_search_no_results(self, mock_search_util):
        """测试无结果查询"""
        mock_search_util.return_value = []
        
        response = self.app.post('/search', data={'query': '不存在的题目'})
        self.assertEqual(response.status_code, 200)
        mock_search_util.assert_called_once_with('不存在的题目')
        
        # 检查返回的HTML是否不包含结果
        html = response.data.decode('utf-8')
        self.assertNotIn('id="question-', html)
    
    def test_search_unauthorized(self):
        """测试未登录用户访问"""
        with self.app.session_transaction() as sess:
            sess.clear()  # 清除会话，模拟未登录状态
            
        response = self.app.post('/search', data={'query': '测试'})
        self.assertEqual(response.status_code, 302)  # 应该重定向到登录页面
        self.assertIn('/login', response.location)

class TestSearchUtil(unittest.TestCase):
    """测试search_util函数的单元测试"""
    
    @patch('handlers.database.get_db')
    def test_search_util_function(self, mock_get_db):
        """测试search_util函数"""
        # 模拟数据库连接和查询结果
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟查询结果
        mock_cursor.fetchall.return_value = [
            {'id': '1', 'stem': '测试题目1'},
            {'id': '2', 'stem': '测试题目2'}
        ]
        
        # 调用被测试函数
        result = search_util('测试')
        
        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[1]['stem'], '测试题目2')
        
        # 验证SQL查询
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        self.assertIn('SELECT id, stem FROM questions WHERE stem LIKE ?', args[0])
        self.assertEqual(args[1][0], '%测试%')

class TestSearchIntegration(unittest.TestCase):
    """搜索功能的集成测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.app = app.test_client()
        self.app.testing = True
        # 创建测试会话
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1  # 模拟已登录用户
    
    @patch('handlers.database.get_db')
    def test_search_integration(self, mock_get_db):
        """测试搜索功能的完整流程"""
        # 模拟数据库连接和查询结果
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟查询结果
        mock_cursor.fetchall.return_value = [
            {'id': '1', 'stem': '集成测试题目1'},
            {'id': '2', 'stem': '集成测试题目2'}
        ]
        
        # 发送搜索请求
        response = self.app.post('/search', data={'query': '集成测试'})
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('集成测试题目1', html)
        self.assertIn('集成测试题目2', html)
        
        # 验证SQL查询
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        self.assertIn('SELECT id, stem FROM questions WHERE stem LIKE ?', args[0])
        self.assertEqual(args[1][0], '%集成测试%')

if __name__ == '__main__':
    unittest.main()