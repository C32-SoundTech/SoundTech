import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from app import app as flask_app

class TestTimedMode(unittest.TestCase):# 测试定时/定量答题模块

    def setUp(self):
        self.app = flask_app.test_client()
        self.app.testing = True
        self.app_context = flask_app.app_context()
        self.app_context.push()
        # 模拟用户登录
        with self.app.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'testuser'

    def tearDown(self):
        self.app_context.pop()

    @patch('app.fetch_random_question_ids')
    @patch('app.start_timed_mode_util')
    def test_start_timed_mode_success(self, mock_start_util, mock_fetch_ids):# 测试定时模式正常启动
        # 设置模拟返回值
        mock_fetch_ids.return_value = [1, 2, 3, 4, 5]
        mock_start_util.return_value = (True, 123)
        
        # 发送请求
        response = self.app.post('/start_timed_mode', data={
            'question_count': '10',
            'duration': '15'
        }, follow_redirects=False)
        
        # 验证结果
        self.assertEqual(response.status_code, 302)
        self.assertIn('/timed_mode', response.location)
        
        # 验证模拟函数调用
        mock_fetch_ids.assert_called_once_with(10)
        mock_start_util.assert_called_once()
        
        # 验证session
        with self.app.session_transaction() as session:
            self.assertEqual(session.get('current_exam_id'), 123)

    @patch('app.fetch_random_question_ids')
    @patch('app.start_timed_mode_util')
    def test_start_timed_mode_default_params(self, mock_start_util, mock_fetch_ids):
        """测试定时模式使用默认参数启动"""
        # 设置模拟返回值
        mock_fetch_ids.return_value = [1, 2, 3, 4, 5]
        mock_start_util.return_value = (True, 123)
        
        # 发送请求，不提供参数
        response = self.app.post('/start_timed_mode', data={}, follow_redirects=False)
        
        # 验证结果
        self.assertEqual(response.status_code, 302)
        
        # 验证模拟函数调用，应使用默认参数
        mock_fetch_ids.assert_called_once_with(5)  # 默认题目数量为5

    @patch('app.start_timed_mode_util')
    def test_start_timed_mode_failure(self, mock_start_util):
        """测试定时模式启动失败"""
        # 设置模拟返回值
        mock_start_util.return_value = (False, None)
        
        # 发送请求
        response = self.app.post('/start_timed_mode', data={
            'question_count': '10',
            'duration': '15'
        }, follow_redirects=True)
        
        # 验证结果
        self.assertIn(b'\xe5\x90\xaf\xe5\x8a\xa8\xe5\xae\x9a\xe6\x97\xb6\xe6\xa8\xa1\xe5\xbc\x8f\xe5\xa4\xb1\xe8\xb4\xa5', response.data)  # "启动定时模式失败"

    @patch('app.timed_mode_util')
    @patch('app.fetch_question')
    def test_timed_mode_valid_session(self, mock_fetch_question, mock_timed_mode_util):
        """测试定时模式页面显示 - 有效会话"""
        # 设置模拟返回值
        mock_timed_mode_util.return_value = {
            'id': 123,
            'user_id': 1,
            'question_ids': json.dumps([1, 2, 3]),
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'duration': 600  # 10分钟
        }
        
        mock_fetch_question.side_effect = lambda qid: {
            'id': qid,
            'stem': f'问题{qid}',
            'options': {'A': '选项A', 'B': '选项B'},
            'answer': 'A',
            'type': '单选题',
            'difficulty': '简单'
        }
        
        # 设置session
        with self.app.session_transaction() as session:
            session['current_exam_id'] = 123
        
        # 发送请求
        response = self.app.get('/timed_mode')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xe9\x97\xae\xe9\xa2\x981', response.data)  # "问题1"
        self.assertIn(b'\xe5\x89\xa9\xe4\xbd\x99\xe6\x97\xb6\xe9\x97\xb4', response.data)  # "剩余时间"

    def test_timed_mode_no_session(self):
        """测试定时模式页面显示 - 无效会话"""
        # 确保session中没有current_exam_id
        with self.app.session_transaction() as session:
            if 'current_exam_id' in session:
                del session['current_exam_id']
        
        # 发送请求
        response = self.app.get('/timed_mode', follow_redirects=True)
        
        # 验证结果
        self.assertIn(b'\xe6\x9c\xaa\xe5\x90\xaf\xe5\x8a\xa8\xe5\xae\x9a\xe6\x97\xb6\xe6\xa8\xa1\xe5\xbc\x8f', response.data)  # "未启动定时模式"

    @patch('app.timed_mode_util')
    def test_timed_mode_time_expired(self, mock_timed_mode_util):
        """测试定时模式页面显示 - 时间已到"""
        # 设置模拟返回值 - 时间已过期
        past_time = datetime.now() - timedelta(minutes=15)
        mock_timed_mode_util.return_value = {
            'id': 123,
            'user_id': 1,
            'question_ids': json.dumps([1, 2, 3]),
            'start_time': past_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            'duration': 600  # 10分钟
        }
        
        # 设置session
        with self.app.session_transaction() as session:
            session['current_exam_id'] = 123
        
        # 发送请求
        response = self.app.get('/timed_mode', follow_redirects=False)
        
        # 验证结果
        self.assertEqual(response.status_code, 302)
        self.assertIn('/submit_timed_mode', response.location)

    @patch('app.exam_exist_util')
    @patch('app.fetch_question')
    @patch('app.get_db')
    def test_submit_timed_mode_success(self, mock_get_db, mock_fetch_question, mock_exam_exist):
        """测试定时模式答案提交 - 正常提交"""
        # 设置模拟返回值
        mock_exam_exist.return_value = True
        
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟查询结果
        mock_cursor.fetchone.return_value = {
            'id': 123,
            'user_id': 1,
            'question_ids': json.dumps([1, 2, 3]),
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'duration': 600
        }
        
        # 模拟fetch_question返回值
        mock_fetch_question.side_effect = lambda qid: {
            'id': qid,
            'stem': f'问题{qid}',
            'options': {'A': '选项A', 'B': '选项B'},
            'answer': 'A',
            'type': '单选题',
            'difficulty': '简单'
        }
        
        # 设置session
        with self.app.session_transaction() as session:
            session['current_exam_id'] = 123
        
        # 发送请求
        response = self.app.post('/submit_timed_mode', data={
            'answer_1': 'A',
            'answer_2': 'A',
            'answer_3': 'B'
        }, follow_redirects=True)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        # 验证数据库操作
        self.assertTrue(mock_cursor.execute.called)

    def test_submit_timed_mode_no_session(self):
        """测试定时模式答案提交 - 无效会话"""
        # 确保session中没有current_exam_id
        with self.app.session_transaction() as session:
            if 'current_exam_id' in session:
                del session['current_exam_id']
        
        # 发送请求
        response = self.app.post('/submit_timed_mode', follow_redirects=True)
        
        # 验证结果
        self.assertIn(b'\xe6\xb2\xa1\xe6\x9c\x89\xe6\xad\xa3\xe5\x9c\xa8\xe8\xbf\x9b\xe8\xa1\x8c\xe7\x9a\x84\xe5\xae\x9a\xe6\x97\xb6\xe6\xa8\xa1\xe5\xbc\x8f', response.data)  # "没有正在进行的定时模式"

if __name__ == '__main__':
    unittest.main()