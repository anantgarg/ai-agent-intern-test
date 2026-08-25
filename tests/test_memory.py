from app.memory.session import SessionStore

def test_sessions_are_isolated():
    store=SessionStore(); store.add('a','user','Canada?')
    assert store.get('b').messages==[]

def test_history_is_bounded():
    store=SessionStore(max_messages=4)
    for i in range(10): store.add('a','user',str(i))
    assert len(store.get('a').messages)==4
