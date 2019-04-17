from functools import wraps
from flask import session, request, redirect, url_for

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if session.get('is_authenticated') != True:
      return redirect(url_for('login', next=request.url))
    return f(*args, **kwargs)
  return decorated_function
