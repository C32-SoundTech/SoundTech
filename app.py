import os
import json
import random
from datetime import UTC, datetime, timedelta

from flask import Flask
from flask import session, request
from flask import flash, jsonify, url_for, redirect, render_template

from werkzeug.security import check_password_hash, generate_password_hash

from handlers.database import get_db
from handlers.authentication import login_required, is_logged_in, get_user_id

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", __name__)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

#############################
# Question Helper Functions #
#############################

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

#########################
# Authentication Routes #
#########################

@app.route("/register", methods=['GET', 'POST'])
def register():
    """
    用户注册路由。
    处理用户注册请求，包括表单验证、用户名重复检查和密码加密存储。
    
    Returns:
        Response: 注册页面或重定向到登录页面
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template("register.html")
            
        if password != confirm_password:
            flash("两次输入的密码不一致", "error")
            return render_template("register.html")
            
        if len(password) < 6:
            flash("密码长度不能少于6个字符", "error")
            return render_template("register.html")
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE username=?', (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash("用户名已存在，请更换用户名", "error")
            return render_template("register.html")
        
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("注册成功，请登录", "success")
        return redirect(url_for("login"))
        
    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    """
    用户登录路由。
    处理用户登录请求，验证用户名和密码，设置会话状态。
    
    Returns:
        Response: 登录页面或重定向到主页面
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template("login.html")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
                
            return redirect(url_for("index"))
        else:
            flash("登录失败，用户名或密码错误", "error")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    """
    用户登出路由。
    清除用户会话信息，重定向到登录页面。
    
    Returns:
        Response: 重定向到登录页面
    """
    session.clear()
    flash("您已成功退出登录", "success")
    return redirect(url_for("login"))

###########################
# Main Application Routes #
###########################

@app.route("/")
@login_required
def index():
    """
    应用主页路由。
    显示应用主页，包含当前用户的顺序答题进度信息。
    
    Returns:
        Response: 渲染的主页模板
    """
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None
    cursor.close()
    conn.close()
    
    return render_template("index.html", current_year=datetime.now(UTC).year, current_seq_qid=current_seq_qid)

@app.route("/reset_history", methods=['POST'])
@login_required
def reset_history():
    """
    重置用户答题历史路由。
    清除当前用户的所有答题历史记录和顺序答题进度。
    
    Returns:
        Response: 重定向到随机题目页面
    """
    user_id = get_user_id()
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE user_id=?', (user_id,))
        cursor.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("答题历史已重置。现在您可以重新开始答题。", "success")
    except Exception as e:
        flash(f"重置历史时出错: {str(e)}", "error")
        
    return redirect(url_for("random_question"))

###################
# Question Routes #
###################

@app.route("/random", methods=['GET'])
@login_required
def random_question():
    """
    随机题目路由。
    为当前用户随机选择一个未答过的题目进行展示。
    
    Returns:
        Response: 渲染的题目页面
    """
    user_id = get_user_id()
    qid = random_question_id(user_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) as answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()
    
    if not qid:
        flash("您已完成所有题目！可以重置历史以重新开始。", "info")
        return render_template("question.html", question=None, answered=answered, total=total)
        
    question = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return render_template("question.html", 
                          question=question, 
                          answered=answered, 
                          total=total,
                          is_favorite=is_fav)

@app.route("/question/<qid>", methods=['GET', 'POST'])
@login_required
def show_question(qid):
    """
    显示指定题目路由。
    展示指定 ID 的题目，处理用户答题提交。
    
    Args:
        qid: 题目 ID
        
    Returns:
        Response: 渲染的题目页面或重定向
    """
    user_id = get_user_id()
    question = fetch_question(qid)
    
    if question is None:
        flash("题目不存在", "error")
        return redirect(url_for("index"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()

    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(question['answer'])))

        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', (user_id, qid, user_answer_str, correct))
        conn.commit()

        cursor.execute('SELECT COUNT(*) AS total FROM questions')
        total = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
        answered = cursor.fetchone()['answered']
        cursor.close()
        conn.close()

        result_msg = "回答正确" if correct else f"回答错误，正确答案：{question['answer']}"
        flash(result_msg, "success" if correct else "error")
        is_fav = is_favorite(user_id, qid)
        
        return render_template("question.html",
                              question=question,
                              result_msg=result_msg,
                              answered=answered,
                              total=total,
                              is_favorite=is_fav)

    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()
    
    is_fav = is_favorite(user_id, qid)

    return render_template("question.html",
                          question=question,
                          answered=answered,
                          total=total,
                          is_favorite=is_fav)

@app.route("/history")
@login_required
def show_history():
    """
    显示答题历史路由。
    展示当前用户的所有答题历史记录。
    
    Returns:
        Response: 渲染的历史页面
    """
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history WHERE user_id=? ORDER BY timestamp DESC', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    history_data = []
    for row in rows:
        q = fetch_question(row['question_id'])
        stem = q['stem'] if q else "题目已删除"
        history_data.append({
            "id": row['id'],
            "question_id": row['question_id'],
            "stem": stem,
            "user_answer": row['user_answer'],
            "correct": row['correct'],
            "timestamp": row['timestamp']
        })
    
    return render_template("history.html", history=history_data)

@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    """
    题目搜索路由。
    根据关键词搜索题目内容。
    
    Returns:
        Response: 渲染的搜索结果页面
    """
    query = request.form.get('query', '')
    results = []
    
    if query:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE stem LIKE ?', ('%'+query+'%',))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for row in rows:
            question = {
                "id": row['id'],
                "stem": row['stem']
            }
            results.append(question)
    
    return render_template("search.html", query=query, results=results)

@app.route("/wrong")
@login_required
def wrong_questions():
    """
    错题集路由。
    显示当前用户所有答错的题目列表。
    
    Returns:
        Response: 渲染的错题页面
    """
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    wrong_ids = set(row['question_id'] for row in rows)
    questions_list = []
    
    for qid in wrong_ids:
        question = fetch_question(qid)
        if question:
            questions_list.append(question)
    
    return render_template("wrong.html", questions=questions_list)

@app.route("/only_wrong")
@login_required
def only_wrong_mode():
    """
    错题练习模式路由。
    随机选择一个用户答错的题目进行练习。
    
    Returns:
        Response: 渲染的题目页面或重定向到主页
    """
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    wrong_ids = [row['question_id'] for row in rows]
    
    if not wrong_ids:
        flash("你没有错题或还未答题", "info")
        return redirect(url_for("index"))
    
    qid = random.choice(wrong_ids)
    question = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return render_template("question.html", question=question, is_favorite=is_fav)

#################
# Browse Routes #
#################

@app.route("/browse")
@login_required
def browse_questions():
    """
    浏览题目路由。
    分页显示所有题目列表，支持页面导航。
    
    Returns:
        Response: 渲染的题目浏览页面
    """
    user_id = get_user_id()
    page = request.args.get('page', 1, type=int)
    question_type = request.args.get('type', '')
    search_query = request.args.get('search', '')
    per_page = 20
    
    conn = get_db()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if question_type and question_type != 'all':
        where_conditions.append('qtype = ?')
        params.append(question_type)
    
    if search_query:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    
    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    count_sql = f'SELECT COUNT(*) as total FROM questions{where_clause}'
    cursor.execute(count_sql, params)
    total = cursor.fetchone()['total']
    
    # Get questions with pagination and filters
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
    
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template("browse.html",
                          questions=questions,
                          total=total,
                          page=page,
                          per_page=per_page,
                          total_pages=total_pages,
                          has_prev=has_prev,
                          has_next=has_next,
                          current_type=question_type,
                          current_search=search_query,
                          available_types=available_types)

#################
# Filter Routes #
#################

@app.route("/filter", methods=['GET', 'POST'])
@login_required
def filter_questions():
    """
    题目过滤路由。
    根据题目类型、难度等条件过滤题目。
    
    Returns:
        Response: 渲染的过滤结果页面
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT category FROM questions WHERE category IS NOT NULL AND category != ""')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != ""')
    difficulties = [row['difficulty'] for row in cursor.fetchall()]

    selected_category = ""
    selected_difficulty = ""
    results = []
    
    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_difficulty = request.form.get('difficulty', '')
        
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
    
    return render_template("filter.html", 
                          categories=categories, 
                          difficulties=difficulties,
                          selected_category=selected_category,
                          selected_difficulty=selected_difficulty,
                          results=results)

####################
# Favorites Routes #
####################

@app.route("/favorite/<qid>", methods=['POST'])
@login_required
def favorite_question(qid):
    """
    收藏题目路由。
    将指定题目添加到用户收藏夹。
    
    Args:
        qid: 题目 ID
        
    Returns:
        Response: JSON 响应表示操作结果
    """
    user_id = get_user_id()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, tag) VALUES (?, ?, ?)', (user_id, qid, ''))
        conn.commit()
        flash("收藏成功！", "success")
    except Exception as e:
        flash(f"收藏失败: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
    
    referrer = request.referrer
    if referrer and "/question/" in referrer:
        return redirect(referrer)
    return redirect(url_for("show_question", qid=qid))

@app.route("/unfavorite/<qid>", methods=['POST'])
@login_required
def unfavorite_question(qid):
    """
    取消收藏题目路由。
    将指定题目从用户收藏夹中移除。
    
    Args:
        qid: 题目 ID
        
    Returns:
        Response: JSON 响应表示操作结果
    """
    user_id = get_user_id()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM favorites WHERE user_id=? AND question_id=?', (user_id, qid))
        conn.commit()
        flash("已取消收藏", "success")
    except Exception as e:
        flash(f"取消收藏失败: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
    
    referrer = request.referrer
    if referrer and "/question/" in referrer:
        return redirect(referrer)
    return redirect(url_for("show_question", qid=qid))

@app.route("/update_tag/<qid>", methods=['POST'])
@login_required
def update_tag(qid):
    """
    更新题目标签路由。
    为收藏的题目添加或更新标签。
    
    Args:
        qid: 题目 ID
        
    Returns:
        Response: JSON 响应表示操作结果
    """
    if not is_logged_in():
        return jsonify({"success": False, "msg": "未登录"}), 401
    
    user_id = get_user_id()
    new_tag = request.form.get('tag', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=?', (new_tag, user_id, qid))
        conn.commit()
        return jsonify({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/favorites")
@login_required
def show_favorites():
    """
    显示收藏夹路由。
    展示当前用户的所有收藏题目。
    
    Returns:
        Response: 渲染的收藏夹页面
    """
    user_id = get_user_id()
    
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
    
    favorites_data = [{'question_id': row['question_id'], 'tag': row['tag'], 'stem': row['stem']} for row in rows]
    
    return render_template("favorites.html", favorites=favorites_data)

##########################
# Sequential Mode Routes #
##########################

@app.route("/sequential_start")
@login_required
def sequential_start():
    """
    顺序模式开始路由。
    开始顺序答题模式，从第一题开始。
    
    Returns:
        Response: 重定向到第一题或渲染页面
    """
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT current_seq_qid FROM users WHERE id=?', (user_id,))
    user_data = cursor.fetchone()
    
    if user_data and user_data['current_seq_qid']:
        current_qid = user_data['current_seq_qid']
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
                flash("题库中没有题目！", "error")
                return redirect(url_for("index"))
            
            current_qid = row['id']
            flash("所有题目已完成，从第一题重新开始。", "info")
        else:
            current_qid = row['id']
        
        cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (current_qid, user_id))
        conn.commit()
    
    cursor.close()
    conn.close()
    return redirect(url_for("show_sequential_question", qid=current_qid))

@app.route("/sequential/<qid>", methods=['GET', 'POST'])
@login_required
def show_sequential_question(qid):
    """
    顺序模式题目显示路由。
    在顺序模式中显示指定题目并处理答题。
    
    Args:
        qid: 题目 ID
        
    Returns:
        Response: 渲染的题目页面或重定向
    """
    user_id = get_user_id()
    question = fetch_question(qid)
    
    if question is None:
        flash("题目不存在", "error")
        return redirect(url_for("index"))

    next_qid = None
    result_msg = None
    user_answer_str = ""
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET current_seq_qid = ? WHERE id = ?", (qid, user_id))
    conn.commit()
    
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(question['answer'])))
        
        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', (user_id, qid, user_answer_str, correct))
        
        cursor.execute('''
            SELECT id FROM questions
            WHERE CAST(id AS INTEGER) > ?
              AND id NOT IN (
                  SELECT question_id FROM history WHERE user_id = ?
              )
            ORDER BY CAST(id AS INTEGER) ASC
            LIMIT 1
        ''', (int(qid), user_id))
        
        row = cursor.fetchone()
        if row:
            next_qid = row['id']
            cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
        else:
            cursor.execute('''
                SELECT id FROM questions
                WHERE id NOT IN (
                    SELECT question_id FROM history WHERE user_id = ?
                )
                ORDER BY CAST(id AS INTEGER) ASC
                LIMIT 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                next_qid = row['id']
                cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?',
                          (next_qid, user_id))
            else:
                cursor.execute('''
                    SELECT id FROM questions
                    ORDER BY CAST(id AS INTEGER) ASC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    next_qid = row['id']
                    cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
                    flash("所有题目已完成，从第一题重新开始。", "info")
                else:
                    cursor.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
            
        result_msg = "回答正确！" if correct else f"回答错误，正确答案：{question['answer']}"
        flash(result_msg, "success" if correct else "error")
    
    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id = ?', (user_id,))
    answered = cursor.fetchone()['answered']
    
    conn.commit()
    cursor.close()
    conn.close()
    
    is_fav = is_favorite(user_id, qid)
    
    return render_template("question.html",
                          question=question,
                          result_msg=result_msg,
                          next_qid=next_qid,
                          sequential_mode=True,
                          user_answer=user_answer_str,
                          answered=answered,
                          total=total,
                          is_favorite=is_fav)

############################
# Timed Mode & Exam Routes #
############################

@app.route("/modes")
@login_required
def modes():
    """
    模式选择路由。
    显示各种答题模式的选择页面。
    
    Returns:
        Response: 渲染的模式选择页面
    """
    return render_template("index.html", mode_select=True, current_year=datetime.now(UTC).year)

@app.route("/start_timed_mode", methods=['POST'])
@login_required
def start_timed_mode():
    """
    开始定时模式路由。
    启动定时答题模式并设置参数。
    
    Returns:
        Response: 重定向到定时模式页面
    """
    user_id = get_user_id()
    
    question_count = int(request.form.get('question_count', 5))
    duration_minutes = int(request.form.get('duration', 10))
    
    question_ids = fetch_random_question_ids(question_count)
    start_time = datetime.now(UTC)
    duration = duration_minutes * 60
    
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
        session['current_exam_id'] = exam_id
        
        return redirect(url_for("timed_mode"))
    except Exception as e:
        flash(f"启动定时模式失败: {str(e)}", "error")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route("/timed_mode")
@login_required
def timed_mode():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动定时模式", "error")
        return redirect(url_for("index"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exam:
        flash("无法找到考试会话", "error")
        return redirect(url_for('index'))
    
    question_ids = json.loads(exam['question_ids'])
    start_time = datetime.strptime(exam['start_time'], "%Y-%m-%d %H:%M:%S.%f")
    end_time = start_time + timedelta(seconds=exam['duration'])
    
    remaining = (end_time - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        return redirect(url_for("submit_timed_mode"))
    
    questions_list = [fetch_question(qid) for qid in question_ids]
    return render_template("timed_mode.html", questions=questions_list, remaining=remaining)

@app.route('/submit_timed_mode', methods=['POST', 'GET'])
@login_required
def submit_timed_mode():
    """
    提交定时模式答案路由。
    处理定时模式中的答案提交。
    
    Returns:
        Response: JSON 响应或重定向
    """
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("没有正在进行的定时模式", "error")
        return redirect(url_for("index"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    
    if not exam:
        cursor.close()
        conn.close()
        flash("无法找到考试会话", "error")
        return redirect(url_for("index"))
    
    question_ids = json.loads(exam['question_ids'])
    
    correct_count = 0
    total = len(question_ids)
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        question = fetch_question(qid)
        
        if not question:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(question['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', (user_id, qid, user_answer_str, correct))
    
    score = (correct_count / total * 100) if total > 0 else 0
    cursor.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    session.pop('current_exam_id', None)
    
    flash(f"定时模式结束！正确率：{correct_count}/{total} = {score:.2f}%", "success" if score >= 60 else "error")
    
    return redirect(url_for("statistics"))

@app.route("/start_exam", methods=['POST'])
@login_required
def start_exam():
    """
    开始考试路由。
    启动考试模式并设置考试参数。
    
    Returns:
        Response: 重定向到考试页面
    """
    user_id = get_user_id()
    
    question_count = int(request.form.get('question_count', 10))
    
    question_ids = fetch_random_question_ids(question_count)
    start_time = datetime.now(UTC)
    duration = 0
    
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
        session['current_exam_id'] = exam_id
        
        return redirect(url_for("exam"))
    except Exception as e:
        flash(f"启动模拟考试失败: {str(e)}", "error")
        return redirect(url_for("index"))
    finally:
        cursor.close()
        conn.close()

@app.route("/exam")
@login_required
def exam():
    """
    考试模式路由。
    进入考试模式进行答题。
    
    Returns:
        Response: 渲染的考试页面
    """
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动考试模式", "error")
        return redirect(url_for("index"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exam:
        flash("无法找到考试", "error")
        return redirect(url_for("index"))
    
    question_ids = json.loads(exam['question_ids'])
    questions_list = [fetch_question(qid) for qid in question_ids]
    
    return render_template("exam.html", questions=questions_list)

@app.route("/submit_exam", methods=['POST'])
@login_required
def submit_exam():
    """
    提交考试答案路由。
    处理考试模式中的答案提交。
    
    Returns:
        Response: 重定向到结果页面
    """
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        return jsonify({"success": False, "msg": "没有正在进行的考试"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    
    if not exam:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "msg": "无法找到考试"}), 404
    
    question_ids = json.loads(exam['question_ids'])
    
    correct_count = 0
    total = len(question_ids)
    question_results = []
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        question = fetch_question(qid)
        
        if not question:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(question['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', (user_id, qid, user_answer_str, correct))
        
        question_results.append({
            "id": qid,
            "stem": question['stem'],
            "user_answer": user_answer_str,
            "correct_answer": question['answer'],
            "is_correct": correct == 1
        })
    
    score = (correct_count / total * 100) if total > 0 else 0
    cursor.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    session.pop('current_exam_id', None)
    
    return jsonify({
        "success": True,
        "correct_count": correct_count,
        "total": total,
        "score": score,
        "results": question_results
    })

#####################
# Statistics Routes #
#####################

@app.route("/statistics")
@login_required
def statistics():
    user_id = get_user_id()
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
    
    return render_template("statistics.html", 
                          overall_accuracy=overall_accuracy,
                          difficulty_stats=difficulty_stats,
                          category_stats=category_stats,
                          worst_questions=worst_questions,
                          recent_exams=recent_exams)

##################
# Error Handlers #
##################

@app.errorhandler(404)
def page_not_found(e):
    """
    404 错误处理函数。
    处理页面未找到的错误。
    
    Args:
        e: 错误对象
        
    Returns:
        Response: 渲染的 404 错误页面
    """
    return render_template("error.html", error_code=404, error_message="页面不存在"), 404

@app.errorhandler(500)
def server_error(e):
    """
    500 错误处理函数。
    处理服务器内部错误。
    
    Args:
        e: 错误对象
        
    Returns:
        Response: 渲染的 500 错误页面
    """
    return render_template("error.html", error_code=500, error_message="服务器内部错误"), 500

#############
# Test Page #
#############

@app.route("/test")
def test():
    """
    测试页面路由。
    用于测试功能的页面。
    
    Returns:
        Response: 渲染的测试页面
    """
    return render_template("test.html")

###############################
# Application Entrytest Point #
###############################

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)
