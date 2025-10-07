
#### 2025.10.7

> 路由函数中的参数错误

* How to solve?
  * 定位到路由函数定义
  * 发现路由中定义了URL参数（如`<qid>`），但函数定义中没有对应的参数
  * 在函数定义中添加对应的参数名
  * 示例修复：

    ```python
    # 错误代码
    @app.route("/question/<qid>")
    @login_required
    def show_question():  # 缺少参数
        question = fetch_question(qid)
        return render_template("question.html", question=question)
    
    # 正确代码
    @app.route("/question/<qid>")
    @login_required
    def show_question(qid):  # 添加参数
        question = fetch_question(qid)
        return render_template("question.html", question=question)
    ```

> 数据库连接未关闭

* How to solve?
  * 定位到数据库操作代码
  * 检查是否在操作完成后关闭了连接
  * 使用`try-finally`结构确保连接总是被关闭
  * 示例修复：

    ```python
    # 错误代码
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
    
    # 正确代码
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

> SQL注入安全漏洞

* How to solve?
  * 定位到SQL查询代码
  * 检查是否直接拼接用户输入到SQL语句中
  * 使用参数化查询替代字符串拼接
  * 示例修复：

    ```python
    # 错误代码
    @app.route("/search")
    def search():
        query = request.args.get('q', '')
        
        conn = get_db()
        cursor = conn.cursor()
        # 直接拼接SQL语句，存在SQL注入风险
        cursor.execute(f"SELECT * FROM questions WHERE stem LIKE '%{query}%'")
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template("search.html", results=results)
    
    # 正确代码
    @app.route("/search")
    def search():
        query = request.args.get('q', '')
        
        conn = get_db()
        cursor = conn.cursor()
        # 使用参数化查询防止SQL注入
        cursor.execute("SELECT * FROM questions WHERE stem LIKE ?", (f'%{query}%',))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template("search.html", results=results)
    ```

> 表单数据处理错误

* How to solve?
  * 定位到表单处理代码
  * 检查是否直接使用`request.form['key']`访问表单数据
  * 使用`request.form.get('key', default)`方法安全获取表单数据
  * 示例修复：

    ```python
    # 错误代码
    @app.route("/update_profile", methods=['POST'])
    @login_required
    def update_profile():
        # 直接访问表单数据，没有检查是否存在
        email = request.form['email']
        nickname = request.form['nickname']
        
        # 更新用户信息
        update_user_profile(get_user_id(), email, nickname)
        return redirect(url_for("profile"))
    
    # 正确代码
    @app.route("/update_profile", methods=['POST'])
    @login_required
    def update_profile():
        # 使用get方法安全获取表单数据
        email = request.form.get('email', '')
        nickname = request.form.get('nickname', '')
        
        # 更新用户信息
        update_user_profile(get_user_id(), email, nickname)
        return redirect(url_for("profile"))
    ```

> 错误的JSON响应格式

* How to solve?
  * 定位到API响应代码
  * 检查是否直接返回Python字典而非JSON响应
  * 使用`jsonify()`函数将字典转换为JSON响应
  * 示例修复：

    ```python
    # 错误代码
    @app.route("/api/question/<qid>")
    def api_question(qid):
        question = fetch_question(qid)
        if question:
            # 直接返回字典，没有使用jsonify
            return question
        else:
            return {"error": "Question not found"}, 404
    
    # 正确代码
    @app.route("/api/question/<qid>")
    def api_question(qid):
        question = fetch_question(qid)
        if question:
            # 使用jsonify转换为JSON响应
            return jsonify(question)
        else:
            return jsonify({"error": "Question not found"}), 404
    ```