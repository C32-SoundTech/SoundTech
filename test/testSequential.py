import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class TestSequentialMode(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        self.app_context.pop()
    
    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
    
    @patch('app.sequential_start_util')
    def test_sequential_start_first_time(self, mock_sequential_start_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = None
        
        # 模拟sequential_start_util返回第一题ID
        mock_sequential_start_util.return_value = ('1', None)
        
        # 访问sequential_start路由
        response = self.client.get('/sequential_start', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_sequential_start_util.assert_called_once_with('testuser', None)
        
        # 检查是否重定向到第一题
        self.assertIn(b'/sequential/1', response.data)
    
    @patch('app.sequential_start_util')
    def test_sequential_start_continue(self, mock_sequential_start_util):# 模拟用户登录并有当前题目ID
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '5'
        
        # 模拟sequential_start_util返回当前题目ID
        mock_sequential_start_util.return_value = ('5', None)
        
        # 访问sequential_start路由
        response = self.client.get('/sequential_start', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_sequential_start_util.assert_called_once_with('testuser', '5')
        
        # 检查是否重定向到当前题目
        self.assertIn(b'/sequential/5', response.data)
    
    @patch('app.sequential_start_util')
    def test_sequential_start_empty_question_bank(self, mock_sequential_start_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = None
        
        # 模拟sequential_start_util返回错误信息
        mock_sequential_start_util.return_value = (None, "题库中没有题目！")
        
        # 访问sequential_start路由
        response = self.client.get('/sequential_start', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"\u9898\u5e93\u4e2d\u6ca1\u6709\u9898\u76ee\uff01", response.data)  # "题库中没有题目！"
    
    @patch('app.sequential_start_util')
    def test_sequential_start_all_completed(self, mock_sequential_start_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '10'
        
        # 模拟sequential_start_util返回第一题ID和完成消息
        mock_sequential_start_util.return_value = ('1', "所有题目已完成，从第一题重新开始。")
        
        # 访问sequential_start路由
        response = self.client.get('/sequential_start', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"\u6240\u6709\u9898\u76ee\u5df2\u5b8c\u6210\uff0c\u4ece\u7b2c\u4e00\u9898\u91cd\u65b0\u5f00\u59cb\u3002", response.data)  # "所有题目已完成，从第一题重新开始。"
        self.assertIn(b'/sequential/1', response.data)
    
    @patch('app.show_sequential_question_util')
    def test_show_sequential_question(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '1'
        
        # 模拟show_sequential_question_util返回题目信息
        mock_question = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_show_sequential_question_util.return_value = (mock_question, 1, 10, None)
        
        # 访问sequential/{qid}路由
        response = self.client.get('/sequential/1')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_show_sequential_question_util.assert_called_once_with('testuser', '1')
        self.assertIn(b"\u6d4b\u8bd5\u9898\u76ee", response.data)  # "测试题目"
        self.assertIn(b"1 / 10", response.data)  # 进度信息
    
    @patch('app.show_sequential_question_util')
    def test_show_sequential_question_not_exist(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '1'
        
        # 模拟show_sequential_question_util返回错误信息
        mock_show_sequential_question_util.return_value = (None, None, None, "题目不存在")
        
        # 访问sequential/{qid}路由
        response = self.client.get('/sequential/999', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"\u9898\u76ee\u4e0d\u5b58\u5728", response.data)  # "题目不存在"
    
    @patch('app.show_sequential_question_util')
    def test_submit_answer_correct(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '1'
        
        # 模拟show_sequential_question_util返回题目信息和下一题ID
        mock_question = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_show_sequential_question_util.return_value = (mock_question, 1, 10, None)
        
        # 模拟提交答案后的处理
        with patch('app.update_history') as mock_update_history:
            with patch('app.get_next_sequential_qid') as mock_get_next_sequential_qid:
                mock_get_next_sequential_qid.return_value = ('2', None)
                
                # 提交正确答案
                response = self.client.post('/sequential/1', data=dict(
                    answer='A'
                ), follow_redirects=True)
                
                # 验证结果
                self.assertEqual(response.status_code, 200)
                mock_update_history.assert_called_once()
                mock_get_next_sequential_qid.assert_called_once_with('testuser', '1')
                self.assertIn(b"\u56de\u7b54\u6b63\u786e\uff01", response.data)  # "回答正确！"
                self.assertIn(b'/sequential/2', response.data)  # 下一题链接
    
    @patch('app.show_sequential_question_util')
    def test_submit_answer_incorrect(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '1'
        
        # 模拟show_sequential_question_util返回题目信息和下一题ID
        mock_question = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_show_sequential_question_util.return_value = (mock_question, 1, 10, None)
        
        # 模拟提交答案后的处理
        with patch('app.update_history') as mock_update_history:
            with patch('app.get_next_sequential_qid') as mock_get_next_sequential_qid:
                mock_get_next_sequential_qid.return_value = ('2', None)
                
                # 提交错误答案
                response = self.client.post('/sequential/1', data=dict(
                    answer='B'
                ), follow_redirects=True)
                
                # 验证结果
                self.assertEqual(response.status_code, 200)
                mock_update_history.assert_called_once()
                mock_get_next_sequential_qid.assert_called_once_with('testuser', '1')
                self.assertIn(b"\u56de\u7b54\u9519\u8bef", response.data)  # "回答错误"
                self.assertIn(b"\u6b63\u786e\u7b54\u6848\uff1aA", response.data)  # "正确答案：A"
                self.assertIn(b'/sequential/2', response.data)  # 下一题链接
    
    @patch('app.show_sequential_question_util')
    def test_next_question_logic(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '1'
        
        # 模拟show_sequential_question_util返回题目信息
        mock_question = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_show_sequential_question_util.return_value = (mock_question, 1, 10, None)
        
        # 模拟提交答案后的处理
        with patch('app.update_history') as mock_update_history:
            with patch('app.get_next_sequential_qid') as mock_get_next_sequential_qid:
                mock_get_next_sequential_qid.return_value = ('2', None)
                
                # 提交答案
                response = self.client.post('/sequential/1', data=dict(
                    answer='A'
                ), follow_redirects=True)
                
                # 验证结果
                self.assertEqual(response.status_code, 200)
                mock_get_next_sequential_qid.assert_called_once_with('testuser', '1')
                
                # 检查session中的current_seq_qid是否更新
                with self.client.session_transaction() as session:
                    self.assertEqual(session['current_seq_qid'], '2')
    
    @patch('app.show_sequential_question_util')
    def test_all_questions_completed(self, mock_show_sequential_question_util):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['current_seq_qid'] = '10'
        
        # 模拟show_sequential_question_util返回题目信息
        mock_question = {
            'id': '10',
            'question': '最后一题',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_show_sequential_question_util.return_value = (mock_question, 10, 10, None)
        
        # 模拟提交答案后的处理
        with patch('app.update_history') as mock_update_history:
            with patch('app.get_next_sequential_qid') as mock_get_next_sequential_qid:
                mock_get_next_sequential_qid.return_value = ('1', "所有题目已完成，从第一题重新开始。")
                
                # 提交答案
                response = self.client.post('/sequential/10', data=dict(
                    answer='A'
                ), follow_redirects=True)
                
                # 验证结果
                self.assertEqual(response.status_code, 200)
                mock_get_next_sequential_qid.assert_called_once_with('testuser', '10')
                self.assertIn(b"\u6240\u6709\u9898\u76ee\u5df2\u5b8c\u6210\uff0c\u4ece\u7b2c\u4e00\u9898\u91cd\u65b0\u5f00\u59cb\u3002", response.data)  # "所有题目已完成，从第一题重新开始。"
                self.assertIn(b'/sequential/1', response.data)  # 第一题链接
                
                # 检查session中的current_seq_qid是否更新为第一题
                with self.client.session_transaction() as session:
                    self.assertEqual(session['current_seq_qid'], '1')

if __name__ == '__main__':
    unittest.main()