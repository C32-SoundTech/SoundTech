import csv
import json
import sqlite3

from werkzeug.security import generate_password_hash


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect("./static/database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_seq_qid TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT, -- JSON stored options
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        tag TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL, -- 'exam' or 'timed'
        question_ids TEXT NOT NULL, -- JSON list
        start_time DATETIME NOT NULL,
        duration INTEGER NOT NULL, -- seconds
        completed BOOLEAN DEFAULT 0,
        score REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()

    cursor.execute('SELECT COUNT(*) as cnt FROM questions')
    if cursor.fetchone()['cnt'] == 0:
        try:
            load_questions_to_db(conn)
        except Exception as e:
            print(f"\033[33m{e}\033[0m")

    cursor.close()
    conn.close()

def load_questions_to_db(conn: sqlite3.Connection) -> None:
    try:
        with open("./resources/questions.csv", 'r', encoding="utf-8") as file:
            reader = csv.DictReader(file)
            cursor = conn.cursor()
            for row in reader:
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if row.get(opt) and row[opt].strip():
                        options[opt] = row[opt]
                cursor.execute(
                    'INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (
                        row["题号"],
                        row["题干"],
                        row["答案"],
                        row["难度"],
                        row["题型"],
                        row.get("类别", "未分类"),
                        json.dumps(options, ensure_ascii=False),
                    ),
                )
            conn.commit()
    except Exception as e:
        print(f"\033[33m{e}\033[0m")

def fetch_question(qid):
    """
    根据题目 ID 从数据库中获取题目信息。
    
    Args:
        qid: 题目 ID
        
    Returns:
        dict: 包含题目信息的字典，如果题目不存在则返回 None
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM questions WHERE id=?', (qid,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        return {
            "id": row['id'],
            "stem": row['stem'],
            "answer": row['answer'],
            "difficulty": row['difficulty'],
            "type": row['qtype'],
            "category": row['category'],
            "options": json.loads(row['options'])
        }
    else:
        return None

def random_question_id(user_id):
    """
    为指定用户随机选择一个未答过的题目 ID。
    
    Args:
        user_id: 用户 ID
        
    Returns:
        int: 随机题目 ID，如果没有未答题目则返回 None
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM questions 
        WHERE id NOT IN (
            SELECT question_id FROM history WHERE user_id=?
        )
        ORDER BY RANDOM() 
        LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        return row['id']
    else:
        return None

def fetch_random_question_ids(num):
    """
    随机获取指定数量的题目 ID 列表。
    
    Args:
        num: 需要获取的题目数量
        
    Returns:
        list: 题目 ID 列表
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM questions ORDER BY RANDOM() LIMIT ?', (num,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row['id'] for row in rows]

def is_favorite(user_id, question_id):
    """
    检查指定题目是否被用户收藏。
    
    Args:
        user_id: 用户 ID
        question_id: 题目 ID
        
    Returns:
        bool: 如果题目被收藏返回 True，否则返回 False
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?', (user_id, question_id))
    is_fav = bool(cursor.fetchone())
    cursor.close()
    conn.close()
    return is_fav

def register_util(username, password) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username=?', (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False
    
    password_hash = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
    conn.commit()
    cursor.close()
    conn.close()
    return True

def login_util(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash FROM users WHERE username=?', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def index_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None
    cursor.close()
    conn.close()
    return current_seq_qid

def reset_history_util(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE user_id=?', (user_id,))
        cursor.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise e

def random_question_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) as answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()
    return answered, total

def show_question_util_get(qid, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()
    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()
    return answered, total

def show_question_util_post(qid, user_id, user_answer_str, correct):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()
    cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', (user_id, qid, user_answer_str, correct))
    conn.commit()

    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()
    return answered, total

def show_history_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history WHERE user_id=? ORDER BY timestamp DESC', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def search_util(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM questions WHERE stem LIKE ?', ('%'+query+'%',))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def wrong_questions_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def only_wrong_mode_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def browse_questions_util(count_sql, params, page, per_page, where_clause, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(count_sql, params)
    total = cursor.fetchone()['total']
    
    offset = (page - 1) * per_page
    query_params = params + [per_page, offset]
    cursor.execute(f'''
        SELECT id, stem, answer, difficulty, qtype, category, options 
        FROM questions 
        {where_clause}
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', query_params)
    
    rows = cursor.fetchall()
    questions = []
    
    for row in rows:
        question_data = {
            "id": row['id'],
            "stem": row['stem'],
            "answer": row['answer'],
            "difficulty": row['difficulty'],
            "type": row['qtype'],
            "category": row['category'],
            "options": json.loads(row['options']) if row['options'] else {}
        }
        
        cursor.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?', (user_id, row['id']))
        question_data['is_favorite'] = bool(cursor.fetchone())
        
        questions.append(question_data)
    
    cursor.execute('SELECT DISTINCT qtype FROM questions WHERE qtype IS NOT NULL AND qtype != ""')
    available_types = [row['qtype'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return total, questions, available_types

def filter_questions_util(selected_category = False, selected_difficulty = False):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT category FROM questions WHERE category IS NOT NULL AND category != ""')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != ""')
    difficulties = [row['difficulty'] for row in cursor.fetchall()]

    selected_category = ""
    selected_difficulty = ""
    results = []
    
    if selected_category and selected_difficulty:
        sql = "SELECT id, stem FROM questions WHERE 1=1"
        params = []
        
        if selected_category:
            sql += " AND category=?"
            params.append(selected_category)
            
        if selected_difficulty:
            sql += " AND difficulty=?"
            params.append(selected_difficulty)
            
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        for row in rows:
            results.append({"id": row['id'], "stem": row['stem']})

    cursor.close()
    conn.close()
    return categories, difficulties, selected_category, selected_difficulty, results

def favorite_question_util(user_id, qid) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, tag) VALUES (?, ?, ?)', (user_id, qid, ''))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()

def unfavorite_question_util(user_id, qid) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM favorites WHERE user_id=? AND question_id=?', (user_id, qid))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()

def update_tag_util(tag, user_id, qid) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=?', (tag, user_id, qid))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        cursor.close()
        conn.close()

def show_favorites_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.question_id, f.tag, q.stem 
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=?
    ''', (user_id,))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def sequential_start_util(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT current_seq_qid FROM users WHERE id=?', (user_id,))
    user_data = cursor.fetchone()
    
    if user_data and user_data['current_seq_qid']:
        current_qid = user_data['current_seq_qid']
        cursor.close()
        conn.close()
        return current_qid, ""
    else:
        cursor.execute('''
            SELECT id
            FROM questions
            WHERE id NOT IN (
                SELECT question_id FROM history WHERE user_id = ?
            )
            ORDER BY CAST(id AS INTEGER) ASC
            LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        flash_info = ""
        
        if row is None:
            cursor.execute('''
                SELECT id
                FROM questions
                ORDER BY CAST(id AS INTEGER) ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            
            if row is None:
                cursor.close()
                conn.close()
                flash_info = "题库中没有题目！"
                return None, flash_info
            
            current_qid = row['id']
            flash_info = "所有题目已完成，从第一题重新开始。"
        else:
            current_qid = row['id']
        
        cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (current_qid, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return current_qid, flash_info

def show_sequential_question_util(qid, user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET current_seq_qid = ? WHERE id = ?", (qid, user_id))
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id = ?', (user_id,))
    answered = cursor.fetchone()['answered']
    
    conn.commit()
    cursor.close()
    conn.close()
    return answered, total 

def start_timed_mode_util(user_id, question_ids, start_time, duration) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'timed', json.dumps(question_ids), start_time, duration))
        
        exam_id = cursor.lastrowid
        conn.commit()
        return True, exam_id
    except Exception as e:
        return False, None
    finally:
        cursor.close()
        conn.close()

def timed_mode_util(exam_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    return exam

def exam_exist_util(exam_id, user_id) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    exam_exist = exam is not None
    cursor.close()
    conn.close()
    return exam_exist


def start_exam_util(user_id, question_ids, start_time, duration) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'exam', json.dumps(question_ids), start_time, duration))
        
        exam_id = cursor.lastrowid
        conn.commit()
        return exam_id
    except Exception as e:
        return None
    finally:
        cursor.close()
        conn.close()

def exam_util(exam_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    return exam

# todo
def submit_exam_util():
    pass

def statistics_util(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total, 
            SUM(correct) as correct_count 
        FROM history 
        WHERE user_id=?
    ''', (user_id,))
    
    row = cursor.fetchone()
    total = row['total'] if row['total'] else 0
    correct_count = row['correct_count'] if row['correct_count'] else 0
    overall_accuracy = (correct_count/total*100) if total>0 else 0
    
    cursor.execute('''
        SELECT 
            q.difficulty, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=?
        GROUP BY q.difficulty
    ''', (user_id,))
    
    difficulty_stats = []
    for row in cursor.fetchall():
        difficulty_stats.append({
            'difficulty': row['difficulty'] or '未分类',
            'total': row['total'],
            'correct_count': row['correct_count'],
            'accuracy': (row['correct_count']/row['total']*100) if row['total']>0 else 0
        })
    
    cursor.execute('''
        SELECT 
            q.category, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=?
        GROUP BY q.category
    ''', (user_id,))
    
    category_stats = []
    for row in cursor.fetchall():
        category_stats.append({
            'category': row['category'] or '未分类',
            'total': row['total'],
            'correct_count': row['correct_count'],
            'accuracy': (row['correct_count']/row['total']*100) if row['total']>0 else 0
        })
    
    cursor.execute('''
        SELECT 
            h.question_id, 
            COUNT(*) as wrong_times, 
            q.stem
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=? AND h.correct=0
        GROUP BY h.question_id
        ORDER BY wrong_times DESC
        LIMIT 10
    ''', (user_id,))
    
    worst_questions = []
    for row in cursor.fetchall():
        worst_questions.append({
            'question_id': row['question_id'],
            'stem': row['stem'],
            'wrong_times': row['wrong_times']
        })
    
    cursor.execute('''
        SELECT 
            id, 
            mode, 
            start_time, 
            score, 
            (SELECT COUNT(*) FROM JSON_EACH(question_ids)) as question_count
        FROM exam_sessions
        WHERE user_id=? AND completed=1
        ORDER BY start_time DESC
        LIMIT 5
    ''', (user_id,))
    
    recent_exams = []
    for row in cursor.fetchall():
        recent_exams.append({
            'id': row['id'],
            'mode': row['mode'],
            'start_time': row['start_time'],
            'score': row['score'],
            'question_count': row['question_count']
        })
    
    cursor.close()
    conn.close()
    return overall_accuracy, difficulty_stats, category_stats, worst_questions, recent_exams

if __name__ != '__main__':
    init_db()
