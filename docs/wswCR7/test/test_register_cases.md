# 注册功能测试用例文档

### 1. 注册页面加载测试
- **测试ID**: T-REGISTER-01
- **测试目的**: 验证注册页面是否正常加载
- **前置条件**: 应用程序正常运行
- **测试步骤**:
  1. 访问 `/register` 路由
- **预期结果**:
  1. 返回状态码 200
  2. 页面内容包含"注册"字样
- **测试类型**: 功能测试

### 2. 正常注册流程测试
- **测试ID**: T-REGISTER-02
- **测试目的**: 验证用户提供有效信息时是否成功注册
- **前置条件**: 应用程序正常运行，register_util 函数可用
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: "testuser"
     - password: "password123"
     - confirm_password: "password123"
- **预期结果**:
  1. register_util 函数被调用一次，参数为 "testuser" 和 "password123"
  2. 页面重定向到登录页面
  3. 页面显示"注册成功"消息
- **测试类型**: 功能测试

### 3. 空用户名测试
- **测试ID**: T-REGISTER-03
- **测试目的**: 验证当用户名为空时的错误处理
- **前置条件**: 应用程序正常运行
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: ""
     - password: "password123"
     - confirm_password: "password123"
- **预期结果**:
  1. 页面显示"用户名和密码不能为空"错误消息
- **测试类型**: 验证测试

### 4. 空密码测试
- **测试ID**: T-REGISTER-04
- **测试目的**: 验证当密码为空时的错误处理
- **前置条件**: 应用程序正常运行
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: "testuser"
     - password: ""
     - confirm_password: ""
- **预期结果**:
  1. 页面显示"用户名和密码不能为空"错误消息
- **测试类型**: 验证测试

### 5. 密码不匹配测试
- **测试ID**: T-REGISTER-05
- **测试目的**: 验证当两次输入的密码不一致时的错误处理
- **前置条件**: 应用程序正常运行
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: "testuser"
     - password: "password123"
     - confirm_password: "password456"
- **预期结果**:
  1. 页面显示"两次输入的密码不一致"错误消息
- **测试类型**: 验证测试

### 6. 密码长度不足测试
- **测试ID**: T-REGISTER-06
- **测试目的**: 验证当密码长度不足时的错误处理
- **前置条件**: 应用程序正常运行
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: "testuser"
     - password: "12345"
     - confirm_password: "12345"
- **预期结果**:
  1. 页面显示"密码长度不能少于6个字符"错误消息
- **测试类型**: 验证测试

### 7. 用户名已存在测试
- **测试ID**: T-REGISTER-07
- **测试目的**: 验证当用户名已存在时的错误处理
- **前置条件**: 应用程序正常运行，register_util 函数返回 False
- **测试步骤**:
  1. 向 `/register` 路由发送 POST 请求，包含:
     - username: "existinguser"
     - password: "password123"
     - confirm_password: "password123"
- **预期结果**:
  1. 页面显示"用户名已存在"错误消息
- **测试类型**: 功能测试

### 8. register_util 函数集成测试
- **测试ID**: T-REGISTER-08
- **测试目的**: 验证 register_util 函数在不同情况下的行为
- **前置条件**: 应用程序正常运行，register_util 函数被模拟
- **测试步骤**:
  1. 模拟 register_util 函数，对于用户名 "existinguser" 返回 False，其他用户名返回 True
  2. 测试新用户注册:
     - username: "newuser"
     - password: "password123"
     - confirm_password: "password123"
  3. 测试已存在用户注册:
     - username: "existinguser"
     - password: "password123"
     - confirm_password: "password123"
- **预期结果**:
  1. 新用户注册成功，页面显示"注册成功"消息
  2. 已存在用户注册失败，页面显示"用户名已存在"错误消息
- **测试类型**: 集成测试
