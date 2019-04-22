from functools import wraps
import os
from flask import session, request, redirect, url_for

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    # redirect to login if in prod and not authenticated
    if os.getenv('PROD') != None and session.get('is_authenticated') != True:
      return redirect(url_for('login', next=request.url))
    return f(*args, **kwargs)
  return decorated_function
