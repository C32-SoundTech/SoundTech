import os
import json
import random
import logging
import logging.handlers
from datetime import UTC, datetime, timedelta

from flask import Flask
from flask import session, request
from flask import flash, jsonify, url_for, redirect, render_template

from werkzeug.security import check_password_hash

from handlers.database import *
from handlers.authentication import login_required, is_logged_in, get_user_id

app = Flask("SoundTech-声像科技")

app.secret_key = os.environ.get("SECRET_KEY", __name__)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

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
        
        if not register_util(username, password):
            flash("用户名已存在，请更换用户名", "error")
            return render_template("register.html")
        
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
        
        app.logger.info(f"用户尝试登录: {username}")
        
        if not username or not password:
            app.logger.warning(f"登录失败 - 用户名或密码为空: {username}")
            flash("用户名和密码不能为空", "error")
            return render_template("login.html")
        
        user = login_util(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            app.logger.info(f"用户登录成功: {username} (ID: {user['id']})")
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
                
            return redirect(url_for("index"))
        else:
            app.logger.warning(f"登录失败 - 用户名或密码错误: {username}")
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
    user_id = session.get('user_id')
    if user_id:
        app.logger.info(f"用户退出登录: ID {user_id}")
    
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
    current_seq_qid = index_util(user_id)
    
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
        reset_history_util(user_id)
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

    answered, total = random_question_util(user_id)
    
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

    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(question['answer'])))

        answered, total = show_question_util_post(qid, user_id, user_answer_str, correct)

        result_msg = "回答正确" if correct else f"回答错误，正确答案：{question['answer']}"
        flash(result_msg, "success" if correct else "error")
        is_fav = is_favorite(user_id, qid)
        
        return render_template("question.html",
                              question=question,
                              result_msg=result_msg,
                              answered=answered,
                              total=total,
                              is_favorite=is_fav)

    answered, total = show_question_util_get(qid, user_id)
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
    rows = show_history_util(user_id)
    
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
        rows = search_util(query)
        
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
    rows = wrong_questions_util(user_id)
    
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
    rows = only_wrong_mode_util(user_id)
    
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
    
    total, questions, available_types = browse_questions_util(count_sql, params, page, per_page, where_clause, user_id)
    
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
    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_difficulty = request.form.get('difficulty', '')
        categories, difficulties, selected_category, selected_difficulty, results = filter_questions_util(selected_category, selected_difficulty)
    else:
        categories, difficulties, selected_category, selected_difficulty, results = filter_questions_util()
    
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
    
    if favorite_question_util(user_id, qid):
        flash("收藏成功！", "success")
    else:
        flash("收藏失败！", "error")
    
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
    
    if unfavorite_question_util(user_id, qid):
        flash("取消收藏成功！", "success")
    else:
        flash("取消收藏失败！", "error")
    
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
    tag = request.form.get('tag', '')
    
    if update_tag_util(tag, user_id, qid):
        return jsonify({"success": True, "msg": "标记更新成功"})
    else:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500

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
    rows = show_favorites_util(user_id)
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
    current_qid, flash_info = sequential_start_util(user_id)
    if current_qid is None:
        return redirect(url_for("index"))
    if flash_info == "题库中没有题目！":
        flash(flash_info, "error")
    elif flash_info == "所有题目已完成，从第一题重新开始。":
        flash(flash_info, "info")
   
    return redirect(url_for("show_sequential_question", qid=current_qid))

# todo
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

    success, exam_id = start_timed_mode_util(user_id, question_ids, start_time, duration)
    if success:
        session['current_exam_id'] = exam_id
        return redirect(url_for("timed_mode"))
    else:
        flash("启动定时模式失败", "error")
        return redirect(url_for('index'))

@app.route("/timed_mode")
@login_required
def timed_mode():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动定时模式", "error")
        return redirect(url_for("index"))
    
    exam = timed_mode_util(exam_id, user_id)
    
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
    
    exam_id = start_exam_util(user_id, question_ids, start_time, duration)
    if exam_id:
        session['current_exam_id'] = exam_id
        return redirect(url_for("exam"))
    else:
        flash("启动模拟考试失败", "error")
        return redirect(url_for("index"))

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

    exam = exam_util(exam_id, user_id)
    
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
    overall_accuracy, difficulty_stats, category_stats, worst_questions, recent_exams = statistics_util(user_id)
    
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
    app.logger.warning(f"404错误 - 页面未找到: {request.url} - IP: {request.remote_addr}")
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
    app.logger.error(f"500错误 - 服务器内部错误: {request.url} - IP: {request.remote_addr} - 错误: {str(e)}")
    return render_template("error.html", error_code=500, error_message="服务器内部错误"), 500


##########################
# Application Middleware #
##########################

@app.before_request
def log_request_info():
    """记录每个请求的基本信息"""
    if request.endpoint not in ['static']:
        app.logger.debug(f"请求: {request.method} {request.url} - IP: {request.remote_addr} - User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

@app.after_request
def log_response_info(response):
    """记录响应信息"""
    if request.endpoint not in ['static']:
        app.logger.debug(f"响应: {response.status_code} - {request.method} {request.url}")
    return response

###########################
# Application Entry Point #
###########################

def setup_logging():
    """配置应用日志系统"""
    os.makedirs('logs', exist_ok=True)
    
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/soundtech.log',
        when='midnight',
        interval=1,
        backupCount=100,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)


if __name__ == '__main__':
    setup_logging()
    app.run(host='0.0.0.0', port=443, ssl_context=('./static/localhost.crt', './static/localhost.key'))

    # from waitress import serve
    # serve(app, host='0.0.0.0', port=80)
