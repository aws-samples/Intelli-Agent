
# set global langgraph app

current_app = None

def set_currrent_app(app):
    global current_app
    current_app = app

def get_current_app():
    assert current_app is not None
    return current_app