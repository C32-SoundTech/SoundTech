# Flask 应用常见错误分析与修复

## 1. 路由函数中的参数错误

### 错误代码
```python
@app.route("/question/<qid>")
@login_required
def show_question():  # 缺少参数
    question = fetch_question(qid)
    return render_template("question.html", question=question)
```

### 错误分析
路由中定义了 `<qid>` 参数，但函数定义中没有对应的参数。Flask 会尝试将 URL 中的 `qid` 传递给函数，但函数没有接收参数的能力，导致运行时错误。

### 正确代码
```python
@app.route("/question/<qid>")
@login_required
def show_question(qid):  # 添加参数
    question = fetch_question(qid)
    return render_template("question.html", question=question)
```

## 2. 数据库连接未关闭

### 错误代码
```python
@app.route("/user_stats")
@login_required
def user_stats():
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM history WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    # 没有关闭数据库连接
    return render_template("statistics.html", total=result['total'])
```

### 错误分析
数据库连接未关闭会导致连接泄漏，长时间运行后可能耗尽数据库连接池，造成应用崩溃。

### 正确代码
```python
@app.route("/user_stats")
@login_required
def user_stats():
    user_id = get_user_id()
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM history WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return render_template("statistics.html", total=result['total'])
    finally:
        cursor.close()
        conn.close()
```

## 3. 表单数据处理错误

### 错误代码
```python
@app.route("/update_profile", methods=['POST'])
@login_required
def update_profile():
    # 直接访问表单数据，没有检查是否存在
    email = request.form['email']
    nickname = request.form['nickname']
    
    # 更新用户信息
    update_user_profile(get_user_id(), email, nickname)
    return redirect(url_for("profile"))
```

### 错误分析
直接使用 `request.form['key']` 访问表单数据，如果表单中没有对应的键，会引发 KeyError 异常。

### 正确代码
```python
@app.route("/update_profile", methods=['POST'])
@login_required
def update_profile():
    # 使用 get 方法安全获取表单数据
    email = request.form.get('email', '')
    nickname = request.form.get('nickname', '')
    
    # 更新用户信息
    update_user_profile(get_user_id(), email, nickname)
    return redirect(url_for("profile"))
```

## 4. 错误的 JSON 响应格式

### 错误代码
```python
@app.route("/api/question/<qid>")
def api_question(qid):
    question = fetch_question(qid)
    if question:
        # 直接返回字典，没有使用 jsonify
        return question
    else:
        return {"error": "Question not found"}, 404
```

### 错误分析
Flask 需要使用 `jsonify()` 函数将 Python 字典转换为 JSON 响应，直接返回字典会导致类型错误。

### 正确代码
```python
@app.route("/api/question/<qid>")
def api_question(qid):
    question = fetch_question(qid)
    if question:
        # 使用 jsonify 转换为 JSON 响应
        return jsonify(question)
    else:
        return jsonify({"error": "Question not found"}), 404
```

## 5. 未处理的异常

### 错误代码
```python
@app.route("/delete_question/<qid>", methods=['POST'])
@login_required
def delete_question(qid):
    # 没有异常处理
    delete_question_from_db(qid)
    flash("题目已删除", "success")
    return redirect(url_for("browse_questions"))
```

### 错误分析
如果删除操作失败（例如数据库错误、外键约束等），未处理的异常会导致 500 服务器错误，用户体验差。

### 正确代码
```python
@app.route("/delete_question/<qid>", methods=['POST'])
@login_required
def delete_question(qid):
    try:
        delete_question_from_db(qid)
        flash("题目已删除", "success")
    except Exception as e:
        app.logger.error(f"删除题目失败: {str(e)}")
        flash(f"删除题目失败: {str(e)}", "error")
    
    return redirect(url_for("browse_questions"))
```

## 6. 安全漏洞：SQL 注入

### 错误代码
```python
@app.route("/search")
def search():
    query = request.args.get('q', '')
    
    conn = get_db()
    cursor = conn.cursor()
    # 直接拼接 SQL 语句，存在 SQL 注入风险
    cursor.execute(f"SELECT * FROM questions WHERE stem LIKE '%{query}%'")
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template("search.html", results=results)
```

### 错误分析
直接将用户输入拼接到 SQL 查询中会导致 SQL 注入漏洞，攻击者可以通过构造特殊的查询字符串来执行恶意 SQL 命令。

### 正确代码
```python
@app.route("/search")
def search():
    query = request.args.get('q', '')
    
    conn = get_db()
    cursor = conn.cursor()
    # 使用参数化查询防止 SQL 注入
    cursor.execute("SELECT * FROM questions WHERE stem LIKE ?", (f'%{query}%',))
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template("search.html", results=results)
```

## 7. 会话管理错误

### 错误代码
```python
@app.route("/login", methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = login_util(username)
    
    if user and check_password_hash(user['password_hash'], password):
        # 直接存储用户对象到会话，可能导致序列化问题
        session['user'] = user
        return redirect(url_for("index"))
    else:
        flash("登录失败", "error")
        return render_template("login.html")
```

### 错误分析
将整个用户对象存储到会话中可能导致序列化问题，因为 Flask 会将会话数据序列化为 JSON。此外，存储敏感信息（如密码哈希）到会话中也是不安全的。

### 正确代码
```python
@app.route("/login", methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = login_util(username)
    
    if user and check_password_hash(user['password_hash'], password):
        # 只存储必要的用户标识信息
        session['user_id'] = user['id']
        return redirect(url_for("index"))
    else:
        flash("登录失败", "error")
        return render_template("login.html")
```

## 8. 错误的重定向处理

### 错误代码
```python
@app.route("/edit_question/<qid>", methods=['GET', 'POST'])
@login_required
def edit_question(qid):
    if request.method == 'POST':
        # 更新题目
        update_question(qid, request.form)
        # 使用相对路径重定向，可能导致错误
        return redirect(f"/question/{qid}")
    
    question = fetch_question(qid)
    return render_template("edit_question.html", question=question)
```

### 错误分析
使用相对路径进行重定向可能导致错误，特别是当应用部署在子目录下时。应该使用 `url_for()` 函数生成正确的 URL。

### 正确代码
```python
@app.route("/edit_question/<qid>", methods=['GET', 'POST'])
@login_required
def edit_question(qid):
    if request.method == 'POST':
        # 更新题目
        update_question(qid, request.form)
        # 使用 url_for 生成正确的 URL
        return redirect(url_for("show_question", qid=qid))
    
    question = fetch_question(qid)
    return render_template("edit_question.html", question=question)
```

## 9. 错误的文件上传处理

### 错误代码
```python
@app.route("/upload", methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("没有文件", "error")
        return redirect(request.url)
        
    file = request.files['file']
    
    # 直接使用用户提供的文件名，存在安全风险
    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    flash("文件上传成功", "success")
    return redirect(url_for("index"))
```

### 错误分析
直接使用用户提供的文件名存在安全风险，可能导致目录遍历攻击或覆盖现有文件。此外，没有验证文件类型和大小。

### 正确代码
```python
import os
from werkzeug.utils import secure_filename

@app.route("/upload", methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("没有文件", "error")
        return redirect(request.url)
        
    file = request.files['file']
    
    if file.filename == '':
        flash("未选择文件", "error")
        return redirect(request.url)
    
    # 检查文件类型
    allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        flash("不允许的文件类型", "error")
        return redirect(request.url)
    
    # 安全处理文件名
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    flash("文件上传成功", "success")
    return redirect(url_for("index"))
```

## 10. 缺少 CSRF 保护

### 错误代码
```python
@app.route("/change_password", methods=['POST'])
@login_required
def change_password():
    # 没有 CSRF 保护
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    if verify_password(get_user_id(), old_password):
        update_password(get_user_id(), new_password)
        flash("密码已更新", "success")
    else:
        flash("原密码错误", "error")
    
    return redirect(url_for("profile"))
```

### 错误分析
没有 CSRF 保护的表单容易受到跨站请求伪造攻击，攻击者可以诱导用户在不知情的情况下提交表单。

### 正确代码
```python
from flask_wtf.csrf import CSRFProtect

# 在应用初始化时添加
csrf = CSRFProtect(app)

@app.route("/change_password", methods=['POST'])
@login_required
def change_password():
    # Flask-WTF 会自动检查 CSRF 令牌
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    if verify_password(get_user_id(), old_password):
        update_password(get_user_id(), new_password)
        flash("密码已更新", "success")
    else:
        flash("原密码错误", "error")
    
    return redirect(url_for("profile"))
```

在模板中添加 CSRF 令牌：
```html
<form method="post" action="{{ url_for('change_password') }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 其他表单字段 -->
    <button type="submit">更改密码</button>
</form>
```