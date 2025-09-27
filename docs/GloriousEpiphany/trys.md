#### 2025.9.27

> 数据库访问报错：**题号**

* How to solve?
  * 定位到`tools\questions.csv`
  * 发现其编码格式为`UTF-8 with BOM`，该系列UTF-8编码会在文件头加上`\ufeff`
  * 故而，在实际的读取过程中，读取到的列名为`"\ufeff题号"`，出现以上错误
  * 将文件编码改为正常`UTF-8`编码，即可解决前序报错

> 以一种访问权限不允许的方式做了一个访问套接字的尝试。

* How to solve?

  * 定位到`app.py`

  * 在文件最后，有如下代码

    ```python
    app.run(host="0.0.0.0", debug=True, port=5000)
    ```

  * 在Windows系统中，绑定到80端口需要管理员权限 
  
  * 