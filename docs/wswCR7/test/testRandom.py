import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class TestRandomMode(unittest.TestCase):
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
    
    @patch('app.random_question_id')
    @patch('app.random_question_util')
    @patch('app.fetch_question')
    @patch('app.is_favorite')
    def test_random_question_with_available_questions(self, mock_is_favorite, mock_fetch_question, 
                                                     mock_random_question_util, mock_random_question_id):# 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 模拟函数返回值
        mock_random_question_id.return_value = '1'
        mock_random_question_util.return_value = (5, 10)  # 已答5题，总共10题
        mock_fetch_question.return_value = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_is_favorite.return_value = False
        
        # 访问random路由
        response = self.client.get('/random')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_random_question_id.assert_called_once_with(1)
        mock_random_question_util.assert_called_once_with(1)
        mock_fetch_question.assert_called_once_with('1')
        mock_is_favorite.assert_called_once_with(1, '1')
        
        # 检查页面内容
        self.assertIn(b'\xe6\xb5\x8b\xe8\xaf\x95\xe9\xa2\x98\xe7\x9b\xae', response.data)  # "测试题目"
        self.assertIn(b'5 / 10', response.data)  # 答题进度
    
    @patch('app.random_question_id')
    @patch('app.random_question_util')
    def test_random_question_all_completed(self, mock_random_question_util, mock_random_question_id):
        # 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 模拟函数返回值 - 所有题目已完成
        mock_random_question_id.return_value = None
        mock_random_question_util.return_value = (10, 10)  # 已答10题，总共10题
        
        # 访问random路由
        response = self.client.get('/random')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_random_question_id.assert_called_once_with(1)
        mock_random_question_util.assert_called_once_with(1)
        
        # 检查页面内容
        self.assertIn(b'\xe6\x82\xa8\xe5\xb7\xb2\xe5\xae\x8c\xe6\x88\x90\xe6\x89\x80\xe6\x9c\x89\xe9\xa2\x98\xe7\x9b\xae', response.data)  # "您已完成所有题目"
        self.assertIn(b'\xe9\x87\x8d\xe7\xbd\xae\xe7\xad\x94\xe9\xa2\x98\xe5\x8e\x86\xe5\x8f\xb2', response.data)  # "重置答题历史"
    
    @patch('app.wrong_questions_util')
    @patch('app.fetch_question')
    def test_wrong_questions_with_wrong_answers(self, mock_fetch_question, mock_wrong_questions_util):
        # 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 模拟函数返回值 - 有错题
        mock_wrong_questions_util.return_value = [{'question_id': '1'}, {'question_id': '2'}]
        mock_fetch_question.side_effect = lambda qid: {
            'id': qid,
            'question': f'测试题目{qid}',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        
        # 访问wrong路由
        response = self.client.get('/wrong')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_wrong_questions_util.assert_called_once_with(1)
        self.assertEqual(mock_fetch_question.call_count, 2)
        
        # 检查页面内容
        self.assertIn(b'\xe6\xb5\x8b\xe8\xaf\x95\xe9\xa2\x98\xe7\x9b\xae1', response.data)  # "测试题目1"
        self.assertIn(b'\xe6\xb5\x8b\xe8\xaf\x95\xe9\xa2\x98\xe7\x9b\xae2', response.data)  # "测试题目2"
    
    @patch('app.only_wrong_mode_util')
    @patch('app.fetch_question')
    @patch('app.is_favorite')
    def test_only_wrong_mode_with_wrong_answers(self, mock_is_favorite, mock_fetch_question, mock_only_wrong_mode_util):
        # 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 模拟函数返回值 - 有错题
        mock_only_wrong_mode_util.return_value = [{'question_id': '1'}, {'question_id': '2'}]
        mock_fetch_question.return_value = {
            'id': '1',
            'question': '测试题目',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '解释'
        }
        mock_is_favorite.return_value = False
        
        # 模拟random.choice选择第一个错题
        with patch('random.choice', return_value='1'):
            # 访问only_wrong路由
            response = self.client.get('/only_wrong')
            
            # 验证结果
            self.assertEqual(response.status_code, 200)
            mock_only_wrong_mode_util.assert_called_once_with(1)
            mock_fetch_question.assert_called_once_with('1')
            mock_is_favorite.assert_called_once_with(1, '1')
            
            # 检查页面内容
            self.assertIn(b'\xe6\xb5\x8b\xe8\xaf\x95\xe9\xa2\x98\xe7\x9b\xae', response.data)  # "测试题目"
    
    @patch('app.only_wrong_mode_util')
    def test_only_wrong_mode_without_wrong_answers(self, mock_only_wrong_mode_util):
        # 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 模拟函数返回值 - 无错题
        mock_only_wrong_mode_util.return_value = []
        
        # 访问only_wrong路由
        response = self.client.get('/only_wrong', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_only_wrong_mode_util.assert_called_once_with(1)
        
        # 检查页面内容
        self.assertIn(b'\xe4\xbd\xa0\xe6\xb2\xa1\xe6\x9c\x89\xe9\x94\x99\xe9\xa2\x98\xe6\x88\x96\xe8\xbf\x98\xe6\x9c\xaa\xe7\xad\x94\xe9\xa2\x98', response.data)  # "你没有错题或还未答题"
    
    @patch('app.reset_history_util')
    def test_reset_history(self, mock_reset_history_util):
        # 模拟用户登录
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'testuser'
            session['user_id'] = 1
        
        # 访问reset_history路由
        response = self.client.post('/reset_history', follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        mock_reset_history_util.assert_called_once_with(1)
        
        # 检查页面内容
        self.assertIn(b'\xe7\xad\x94\xe9\xa2\x98\xe5\x8e\x86\xe5\x8f\xb2\xe5\xb7\xb2\xe9\x87\x8d\xe7\xbd\xae', response.data)  # "答题历史已重置"
    
    @patch('app.fetch_random_question_ids')
    def test_fetch_random_question_ids(self, mock_fetch_random_question_ids):
        # 模拟函数返回值
        mock_fetch_random_question_ids.return_value = ['1', '2', '3', '4', '5']
        
        # 调用函数
        from handlers.database import fetch_random_question_ids
        result = fetch_random_question_ids(5)
        
        # 验证结果
        self.assertEqual(len(result), 5)
        self.assertEqual(result, ['1', '2', '3', '4', '5'])
        mock_fetch_random_question_ids.assert_called_once_with(5)

if __name__ == '__main__':
    unittest.main()