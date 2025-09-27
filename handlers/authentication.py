from functools import wraps

from flask import session, request
from flask import flash, url_for, redirect

def login_required(function):
    """
    装饰器函数，用于检查用户是否已登录。
    如果用户未登录，则重定向到登录页面。
    
    Args:
        function: 需要登录验证的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("请先登录后再访问该页面", "error")
            return redirect(url_for("login", next=request.url))
        return function(*args, **kwargs)
    return decorated_function

def is_logged_in() -> bool:
    """
    检查当前用户是否已登录。
    
    Returns:
        bool: 如果用户已登录返回 True，否则返回 False
    """
    return "user_id" in session

def get_user_id() -> int:
    """
    获取当前登录用户的 ID。
    
    Returns:
        int: 当前用户的 ID，如果未登录则返回 None
    """
    return session.get("user_id")