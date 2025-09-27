import csv
import json
import sqlite3


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

if __name__ != '__main__':
    init_db()
