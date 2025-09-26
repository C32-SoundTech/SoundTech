import os
import json
import random
from datetime import UTC, datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from werkzeug.security import check_password_hash, generate_password_hash

from handlers.database import get_db

app = FastAPI(title="SoundTech Question System")

# 添加会话中间件
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")
app.add_middleware(SessionMiddleware, secret_key=app.secret_key)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def url_for(name: str, **params):
    if name == "static":
        filename = params.get("filename", "")
        return f"/static/{filename}"
    # 对于其他路由，返回路径
    route_map = {
        "index": "/",
        "register": "/register",
        "login": "/login",
        "logout": "/logout",
        "random_question": "/random",
        "show_history": "/history",
        "search": "/search",
        "show_wrong": "/wrong",
        "only_wrong": "/only_wrong",
        "browse": "/browse",
        "filter_questions": "/filter",
        "show_favorites": "/favorites",
        "sequential_start": "/sequential_start",
        "start_timed_mode": "/start_timed_mode",
        "start_exam": "/start_exam",
        "statistics": "/statistics",
        "modes": "/modes",
        "reset_history": "/reset_history"
    }
    
    # 处理带参数的路由
    if name == "show_question":
        qid = params.get("qid", "")
        return f"/question/{qid}"
    elif name == "show_sequential_question":
        qid = params.get("qid", "")
        return f"/sequential/{qid}"
    elif name == "favorite_question":
        qid = params.get("qid", "")
        return f"/favorite/{qid}"
    elif name == "unfavorite_question":
        qid = params.get("qid", "")
        return f"/unfavorite/{qid}"
    elif name == "update_tag":
        qid = params.get("qid", "")
        return f"/update_tag/{qid}"
    
    return route_map.get(name, "/")

def get_flashed_messages(with_categories=False):
    """获取Flash消息的函数，兼容Flask模板"""
    return []

templates.env.globals["url_for"] = url_for
templates.env.globals["get_flashed_messages"] = get_flashed_messages

##################
# Authentication #
##################

def is_logged_in(request: Request) -> bool:
    """检查当前用户是否已登录"""
    return "user_id" in request.session

def get_user_id(request: Request) -> Optional[int]:
    """获取当前登录用户的 ID"""
    return request.session.get("user_id")

def login_required(request: Request):
    """登录验证依赖"""
    if not is_logged_in(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="请先登录后再访问该页面",
            headers={"Location": "/login"}
        )
    return get_user_id(request)

def flash_message(request: Request, message: str, category: str = "info"):
    """添加flash消息"""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"message": message, "category": category})

def get_flash_messages(request: Request) -> List[Dict[str, str]]:
    """获取并清除闪现消息"""
    messages = request.session.get("flash_messages", [])
    # request.session["flash_messages"] = []
    return messages

#############################
# Question Helper Functions #
#############################

def fetch_question(qid: str) -> Optional[Dict[str, Any]]:
    """根据题目 ID 从数据库中获取题目信息"""
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

def random_question_id(user_id: int) -> Optional[str]:
    """为指定用户随机选择一个未答过的题目 ID"""
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

def fetch_random_question_ids(num: int) -> List[str]:
    """随机获取指定数量的题目 ID 列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM questions ORDER BY RANDOM() LIMIT ?', (num,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row['id'] for row in rows]

def is_favorite(user_id: int, question_id: str) -> bool:
    """检查指定题目是否被用户收藏"""
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

@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    """显示注册页面"""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/register")
async def register_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """处理用户注册"""
    if not username or not password:
        flash_message(request, "用户名和密码不能为空", "error")
        return RedirectResponse(url="/register", status_code=302)
        
    if password != confirm_password:
        flash_message(request, "两次输入的密码不一致", "error")
        return RedirectResponse(url="/register", status_code=302)
        
    if len(password) < 6:
        flash_message(request, "密码长度不能少于6个字符", "error")
        return RedirectResponse(url="/register", status_code=302)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username=?', (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        flash_message(request, "用户名已存在，请更换用户名", "error")
        return RedirectResponse(url="/register", status_code=302)
    
    password_hash = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash_message(request, "注册成功，请登录", "success")
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    """显示登录页面"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """处理用户登录"""
    if not username or not password:
        flash_message(request, "用户名和密码不能为空", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash FROM users WHERE username=?', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        request.session['user_id'] = user['id']
        
        next_page = request.query_params.get('next')
        if next_page and next_page.startswith('/'):
            return RedirectResponse(url=next_page, status_code=302)
            
        return RedirectResponse(url="/", status_code=302)
    else:
        flash_message(request, "登录失败，用户名或密码错误", "error")
        return RedirectResponse(url="/login", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """用户登出"""
    request.session.clear()
    flash_message(request, "您已成功退出登录", "success")
    return RedirectResponse(url="/login", status_code=302)

###########################
# Main Application Routes #
###########################

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user_id: int = Depends(login_required)):
    """应用主页"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None
    cursor.close()
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_year": datetime.now(UTC).year,
        "current_seq_qid": current_seq_qid,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/reset_history")
async def reset_history(request: Request, user_id: int = Depends(login_required)):
    """重置用户答题历史"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE user_id=?', (user_id,))
        cursor.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash_message(request, "答题历史已重置。现在您可以重新开始答题。", "success")
    except Exception as e:
        flash_message(request, f"重置历史时出错: {str(e)}", "error")
        
    return RedirectResponse(url="/random", status_code=302)

###################
# Question Routes #
###################

@app.get("/random", response_class=HTMLResponse)
async def random_question(request: Request, user_id: int = Depends(login_required)):
    """随机题目"""
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
        flash_message(request, "您已完成所有题目！可以重置历史以重新开始。", "info")
        return templates.TemplateResponse("question.html", {
            "request": request,
            "question": None,
            "answered": answered,
            "total": total,
            "flash_messages": get_flash_messages(request)
        })
        
    question = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "answered": answered,
        "total": total,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/question/{qid}", response_class=HTMLResponse)
async def show_question_get(request: Request, qid: str, user_id: int = Depends(login_required)):
    """显示指定题目"""
    question = fetch_question(qid)
    
    if question is None:
        flash_message(request, "题目不存在", "error")
        return RedirectResponse(url="/", status_code=302)

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
    
    is_fav = is_favorite(user_id, qid)

    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "answered": answered,
        "total": total,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/question/{qid}")
async def show_question_post(
    request: Request, 
    qid: str, 
    user_id: int = Depends(login_required),
    answer: List[str] = Form(default=[])
):
    """处理题目答案提交"""
    question = fetch_question(qid)
    
    if question is None:
        flash_message(request, "题目不存在", "error")
        return RedirectResponse(url="/", status_code=302)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()

    user_answer_str = "".join(sorted(answer))
    correct = int(user_answer_str == "".join(sorted(question['answer'])))

    cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', 
                   (user_id, qid, user_answer_str, correct))
    conn.commit()

    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
    answered = cursor.fetchone()['answered']
    cursor.close()
    conn.close()

    result_msg = "回答正确" if correct else f"回答错误，正确答案：{question['answer']}"
    flash_message(request, result_msg, "success" if correct else "error")
    is_fav = is_favorite(user_id, qid)
    
    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "result_msg": result_msg,
        "user_answer": answer,
        "answered": answered,
        "total": total,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/history", response_class=HTMLResponse)
async def show_history(request: Request, user_id: int = Depends(login_required)):
    """显示答题历史"""
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
    
    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": history_data,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/search", response_class=HTMLResponse)
async def search_get(request: Request, user_id: int = Depends(login_required)):
    """显示搜索页面"""
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": "",
        "results": [],
        "flash_messages": get_flash_messages(request)
    })

@app.post("/search", response_class=HTMLResponse)
async def search_post(
    request: Request, 
    user_id: int = Depends(login_required),
    query: str = Form(default="")
):
    """题目搜索"""
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
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": query,
        "results": results,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/wrong", response_class=HTMLResponse)
async def wrong_questions(request: Request, user_id: int = Depends(login_required)):
    """错题集"""
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
    
    return templates.TemplateResponse("wrong.html", {
        "request": request,
        "questions": questions_list,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/only_wrong", response_class=HTMLResponse)
async def only_wrong_mode(request: Request, user_id: int = Depends(login_required)):
    """错题练习模式"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    wrong_ids = [row['question_id'] for row in rows]
    
    if not wrong_ids:
        flash_message(request, "你没有错题或还未答题", "info")
        return RedirectResponse(url="/", status_code=302)
    
    qid = random.choice(wrong_ids)
    question = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

#################
# Browse Routes #
#################

@app.get("/browse", response_class=HTMLResponse)
async def browse_questions(
    request: Request, 
    user_id: int = Depends(login_required),
    page: int = 1,
    type: str = "",
    search: str = ""
):
    """浏览题目"""
    per_page = 20
    
    conn = get_db()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if type and type != 'all':
        where_conditions.append('qtype = ?')
        params.append(type)
    
    if search:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search + '%', '%' + search + '%'])
    
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
    
    return templates.TemplateResponse("browse.html", {
        "request": request,
        "questions": questions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "current_type": type,
        "current_search": search,
        "available_types": available_types,
        "flash_messages": get_flash_messages(request)
    })

#################
# Filter Routes #
#################

@app.get("/filter", response_class=HTMLResponse)
async def filter_questions_get(request: Request, user_id: int = Depends(login_required)):
    """显示过滤页面"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT category FROM questions WHERE category IS NOT NULL AND category != ""')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != ""')
    difficulties = [row['difficulty'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    
    return templates.TemplateResponse("filter.html", {
        "request": request,
        "categories": categories,
        "difficulties": difficulties,
        "selected_category": "",
        "selected_difficulty": "",
        "results": [],
        "flash_messages": get_flash_messages(request)
    })

@app.post("/filter", response_class=HTMLResponse)
async def filter_questions_post(
    request: Request,
    user_id: int = Depends(login_required),
    category: str = Form(default=""),
    difficulty: str = Form(default="")
):
    """题目过滤"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT category FROM questions WHERE category IS NOT NULL AND category != ""')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != ""')
    difficulties = [row['difficulty'] for row in cursor.fetchall()]

    results = []
    
    sql = "SELECT id, stem FROM questions WHERE 1=1"
    params = []
    
    if category:
        sql += " AND category=?"
        params.append(category)
        
    if difficulty:
        sql += " AND difficulty=?"
        params.append(difficulty)
        
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    for row in rows:
        results.append({"id": row['id'], "stem": row['stem']})

    cursor.close()
    conn.close()
    
    return templates.TemplateResponse("filter.html", {
        "request": request,
        "categories": categories,
        "difficulties": difficulties,
        "selected_category": category,
        "selected_difficulty": difficulty,
        "results": results,
        "flash_messages": get_flash_messages(request)
    })

####################
# Favorites Routes #
####################

@app.post("/favorite/{qid}")
async def favorite_question(request: Request, qid: str, user_id: int = Depends(login_required)):
    """收藏题目"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, tag) VALUES (?, ?, ?)', (user_id, qid, ''))
        conn.commit()
        flash_message(request, "收藏成功！", "success")
    except Exception as e:
        flash_message(request, f"收藏失败: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
    
    referrer = request.headers.get("referer")
    if referrer and "/question/" in referrer:
        return RedirectResponse(url=referrer, status_code=302)
    return RedirectResponse(url=f"/question/{qid}", status_code=302)

@app.post("/unfavorite/{qid}")
async def unfavorite_question(request: Request, qid: str, user_id: int = Depends(login_required)):
    """取消收藏题目"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM favorites WHERE user_id=? AND question_id=?', (user_id, qid))
        conn.commit()
        flash_message(request, "已取消收藏", "success")
    except Exception as e:
        flash_message(request, f"取消收藏失败: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
    
    referrer = request.headers.get("referer")
    if referrer and "/question/" in referrer:
        return RedirectResponse(url=referrer, status_code=302)
    return RedirectResponse(url=f"/question/{qid}", status_code=302)

@app.post("/update_tag/{qid}")
async def update_tag(request: Request, qid: str, user_id: int = Depends(login_required), tag: str = Form(default="")):
    """更新题目标签"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=?', (tag, user_id, qid))
        conn.commit()
        return JSONResponse({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return JSONResponse({"success": False, "msg": f"更新失败: {str(e)}"}, status_code=500)
    finally:
        cursor.close()
        conn.close()

@app.get("/favorites", response_class=HTMLResponse)
async def show_favorites(request: Request, user_id: int = Depends(login_required)):
    """显示收藏夹"""
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
    
    return templates.TemplateResponse("favorites.html", {
        "request": request,
        "favorites": favorites_data,
        "flash_messages": get_flash_messages(request)
    })

##########################
# Sequential Mode Routes #
##########################

@app.get("/sequential_start")
async def sequential_start(request: Request, user_id: int = Depends(login_required)):
    """顺序模式开始"""
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
                flash_message(request, "题库中没有题目！", "error")
                return RedirectResponse(url="/", status_code=302)
            
            current_qid = row['id']
            flash_message(request, "所有题目已完成，从第一题重新开始。", "info")
        else:
            current_qid = row['id']
        
        cursor.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (current_qid, user_id))
        conn.commit()
    
    cursor.close()
    conn.close()
    return RedirectResponse(url=f"/sequential/{current_qid}", status_code=302)

@app.get("/sequential/{qid}", response_class=HTMLResponse)
async def show_sequential_question_get(request: Request, qid: str, user_id: int = Depends(login_required)):
    """顺序模式题目显示"""
    question = fetch_question(qid)
    
    if question is None:
        flash_message(request, "题目不存在", "error")
        return RedirectResponse(url="/", status_code=302)

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET current_seq_qid = ? WHERE id = ?", (qid, user_id))
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id = ?', (user_id,))
    answered = cursor.fetchone()['answered']
    
    cursor.close()
    conn.close()
    
    is_fav = is_favorite(user_id, qid)
    
    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "next_qid": None,
        "sequential_mode": True,
        "user_answer": "",
        "answered": answered,
        "total": total,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/sequential/{qid}")
async def show_sequential_question_post(
    request: Request, 
    qid: str, 
    user_id: int = Depends(login_required),
    answer: List[str] = Form(default=[])
):
    """顺序模式题目答案处理"""
    question = fetch_question(qid)
    
    if question is None:
        flash_message(request, "题目不存在", "error")
        return RedirectResponse(url="/", status_code=302)

    next_qid = None
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET current_seq_qid = ? WHERE id = ?", (qid, user_id))
    conn.commit()
    
    user_answer_str = "".join(sorted(answer))
    correct = int(user_answer_str == "".join(sorted(question['answer'])))
    
    cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', 
                   (user_id, qid, user_answer_str, correct))
    
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
                flash_message(request, "所有题目已完成，从第一题重新开始。", "info")
            else:
                cursor.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        
    result_msg = "回答正确！" if correct else f"回答错误，正确答案：{question['answer']}"
    flash_message(request, result_msg, "success" if correct else "error")
    
    cursor.execute('SELECT COUNT(*) AS total FROM questions')
    total = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id = ?', (user_id,))
    answered = cursor.fetchone()['answered']
    
    conn.commit()
    cursor.close()
    conn.close()
    
    is_fav = is_favorite(user_id, qid)
    
    return templates.TemplateResponse("question.html", {
        "request": request,
        "question": question,
        "result_msg": result_msg,
        "next_qid": next_qid,
        "sequential_mode": True,
        "user_answer": user_answer_str,
        "answered": answered,
        "total": total,
        "is_favorite": is_fav,
        "flash_messages": get_flash_messages(request)
    })

############################
# Timed Mode & Exam Routes #
############################

@app.get("/modes", response_class=HTMLResponse)
async def modes(request: Request, user_id: int = Depends(login_required)):
    """模式选择"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mode_select": True,
        "current_year": datetime.now(UTC).year,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/start_timed_mode")
async def start_timed_mode(
    request: Request,
    user_id: int = Depends(login_required),
    question_count: int = Form(default=5),
    duration: int = Form(default=10)
):
    """开始定时模式"""
    question_ids = fetch_random_question_ids(question_count)
    start_time = datetime.now(UTC)
    duration_seconds = duration * 60
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'timed', json.dumps(question_ids), start_time, duration_seconds))
        
        exam_id = cursor.lastrowid
        conn.commit()
        request.session['current_exam_id'] = exam_id
        
        return RedirectResponse(url="/timed_mode", status_code=302)
    except Exception as e:
        flash_message(request, f"启动定时模式失败: {str(e)}", "error")
        return RedirectResponse(url="/", status_code=302)
    finally:
        cursor.close()
        conn.close()

@app.get("/timed_mode", response_class=HTMLResponse)
async def timed_mode(request: Request, user_id: int = Depends(login_required)):
    """定时模式"""
    exam_id = request.session.get('current_exam_id')
    
    if not exam_id:
        flash_message(request, "未启动定时模式", "error")
        return RedirectResponse(url="/", status_code=302)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exam:
        flash_message(request, "无法找到考试会话", "error")
        return RedirectResponse(url="/", status_code=302)
    
    question_ids = json.loads(exam['question_ids'])
    start_time = datetime.strptime(exam['start_time'], "%Y-%m-%d %H:%M:%S.%f")
    end_time = start_time + timedelta(seconds=exam['duration'])
    
    remaining = (end_time - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        return RedirectResponse(url="/submit_timed_mode", status_code=302)
    
    questions_list = [fetch_question(qid) for qid in question_ids]
    return templates.TemplateResponse("timed_mode.html", {
        "request": request,
        "questions": questions_list,
        "remaining": remaining,
        "flash_messages": get_flash_messages(request)
    })

@app.get("/submit_timed_mode")
async def submit_timed_mode_get(request: Request, user_id: int = Depends(login_required)):
    """提交定时模式答案（GET请求处理）"""
    return await submit_timed_mode_post(request, user_id)

@app.post("/submit_timed_mode")
async def submit_timed_mode_post(request: Request, user_id: int = Depends(login_required)):
    """提交定时模式答案"""
    exam_id = request.session.get('current_exam_id')
    
    if not exam_id:
        flash_message(request, "没有正在进行的定时模式", "error")
        return RedirectResponse(url="/", status_code=302)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    
    if not exam:
        cursor.close()
        conn.close()
        flash_message(request, "无法找到考试会话", "error")
        return RedirectResponse(url="/", status_code=302)
    
    question_ids = json.loads(exam['question_ids'])
    
    correct_count = 0
    total = len(question_ids)
    
    # 处理表单数据
    form_data = await request.form()
    
    for qid in question_ids:
        user_answer = form_data.getlist(f'answer_{qid}')
        question = fetch_question(qid)
        
        if not question:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(question['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', 
                       (user_id, qid, user_answer_str, correct))
    
    score = (correct_count / total * 100) if total > 0 else 0
    cursor.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    request.session.pop('current_exam_id', None)
    
    flash_message(request, f"定时模式结束！正确率：{correct_count}/{total} = {score:.2f}%", 
                  "success" if score >= 60 else "error")
    
    return RedirectResponse(url="/statistics", status_code=302)

@app.post("/start_exam")
async def start_exam(
    request: Request,
    user_id: int = Depends(login_required),
    question_count: int = Form(default=10)
):
    """开始考试"""
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
        request.session['current_exam_id'] = exam_id
        
        return RedirectResponse(url="/exam", status_code=302)
    except Exception as e:
        flash_message(request, f"启动模拟考试失败: {str(e)}", "error")
        return RedirectResponse(url="/", status_code=302)
    finally:
        cursor.close()
        conn.close()

@app.get("/exam", response_class=HTMLResponse)
async def exam(request: Request, user_id: int = Depends(login_required)):
    """考试模式"""
    exam_id = request.session.get('current_exam_id')
    
    if not exam_id:
        flash_message(request, "未启动考试模式", "error")
        return RedirectResponse(url="/", status_code=302)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exam:
        flash_message(request, "无法找到考试", "error")
        return RedirectResponse(url="/", status_code=302)
    
    question_ids = json.loads(exam['question_ids'])
    questions_list = [fetch_question(qid) for qid in question_ids]
    
    return templates.TemplateResponse("exam.html", {
        "request": request,
        "questions": questions_list,
        "flash_messages": get_flash_messages(request)
    })

@app.post("/submit_exam")
async def submit_exam(request: Request, user_id: int = Depends(login_required)):
    """提交考试答案"""
    exam_id = request.session.get('current_exam_id')
    
    if not exam_id:
        return JSONResponse({"success": False, "msg": "没有正在进行的考试"}, status_code=400)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = cursor.fetchone()
    
    if not exam:
        cursor.close()
        conn.close()
        return JSONResponse({"success": False, "msg": "无法找到考试"}, status_code=404)
    
    question_ids = json.loads(exam['question_ids'])
    
    correct_count = 0
    total = len(question_ids)
    question_results = []
    
    # 处理表单数据
    form_data = await request.form()
    
    for qid in question_ids:
        user_answer = form_data.getlist(f'answer_{qid}')
        question = fetch_question(qid)
        
        if not question:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(question['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        cursor.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)', 
                       (user_id, qid, user_answer_str, correct))
        
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
    
    request.session.pop('current_exam_id', None)
    
    return JSONResponse({
        "success": True,
        "correct_count": correct_count,
        "total": total,
        "score": score,
        "results": question_results
    })

#####################
# Statistics Routes #
#####################

@app.get("/statistics", response_class=HTMLResponse)
async def statistics(request: Request, user_id: int = Depends(login_required)):
    """统计页面"""
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
    
    return templates.TemplateResponse("statistics.html", {
        "request": request,
        "overall_accuracy": overall_accuracy,
        "difficulty_stats": difficulty_stats,
        "category_stats": category_stats,
        "worst_questions": worst_questions,
        "recent_exams": recent_exams,
        "flash_messages": get_flash_messages(request)
    })

##################
# Error Handlers #
##################

@app.exception_handler(404)
async def page_not_found(request: Request, exc: HTTPException):
    """404 错误处理"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": 404,
        "error_message": "页面不存在"
    }, status_code=404)

@app.exception_handler(500)
async def server_error(request: Request, exc: HTTPException):
    """500 错误处理"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": 500,
        "error_message": "服务器内部错误"
    }, status_code=500)

#############
# Test Page #
#############

@app.get("/test", response_class=HTMLResponse)
async def test(request: Request):
    """测试页面"""
    return templates.TemplateResponse("test.html", {
        "request": request,
        "flash_messages": get_flash_messages(request)
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)