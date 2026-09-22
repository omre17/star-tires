import re
import sqlite3
from datetime import datetime
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from services import calculate_hours, weekly_hours

@pytest.fixture
def app(tmp_path):
    a=create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite3'), 'SECRET_KEY':'test-only-secret-'*4,'DEMO_MODE':True})
    assert a.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    assert a.test_cli_runner().invoke(args=['seed-demo']).exit_code == 0
    return a

@pytest.fixture
def client(app): return app.test_client()

def token(c):
    return re.search(r'name="csrf_token" value="([^"]+)"',c.get('/').get_data(as_text=True)).group(1)

def post(c,path,data=None):
    return c.post(path,data={**(data or {}),'csrf_token':token(c)})

def login(c,role='worker'):
    assert post(c,'/demo-login/'+role).status_code == 302

def test_routes_and_csrf(client):
    assert client.get('/login').status_code==200
    for path in ['/work-session','/worker_report','/inventory','/payroll','/ai-helper']:
        assert client.get(path,follow_redirects=True).status_code==200
    assert client.post('/work',data={'action':'start'}).status_code==400
    assert client.get('/missing').status_code==404

def test_role_and_logout(client):
    login(client)
    assert client.get('/inventory').status_code==403
    assert client.get('/payroll').status_code==403
    assert client.get('/logout').status_code==405
    assert post(client,'/logout').status_code==302
    assert client.get('/worker_report').status_code==302

@pytest.mark.parametrize('quantity',['','x','-1','0','1.5','100001'])
def test_bad_inventory(client,quantity):
    login(client,'manager')
    assert post(client,'/inventory',{'tire_type':'TEST','quantity':quantity}).status_code==400

def test_inventory_and_prg(client,app):
    login(client,'manager')
    for q in ['5','2']:
        assert post(client,'/inventory',{'tire_type':'TEST','quantity':q}).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute("SELECT quantity FROM inventory WHERE tire_type='TEST'").fetchone()[0]==7
    assert post(client,'/inventory',{'tire_type':' ','quantity':'2'}).status_code==400
    assert client.get('/inventory').status_code==200

def test_attendance(client):
    login(client)
    for action,status in [('end',409),('start',302),('start',409),('end',302),('end',409),('oops',400)]:
        assert post(client,'/work',{'action':action}).status_code==status
    assert client.get('/worker_report').status_code==200

def test_manager_cannot_clock(client):
    login(client,'manager')
    assert post(client,'/work',{'action':'start'}).status_code==403
    assert client.get('/payroll').status_code==200

def test_real_login_hashes_and_limit(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',('test',generate_password_hash('a-long-test-password'),'worker'))
    assert post(client,'/login',{'username':'test','password':'a-long-test-password'}).status_code==302
    post(client,'/logout')
    for _ in range(9):
        assert post(client,'/login',{'username':'test','password':'wrong'}).status_code==401
    assert post(client,'/login',{'username':'test','password':'wrong'}).status_code==429

def test_weekly_calculation():
    events=[{'action':'start','timestamp':'2026-09-19 23:00:00'}, {'action':'end','timestamp':'2026-09-20 02:00:00'}, {'action':'start','timestamp':'2026-09-20 05:00:00'}]
    assert calculate_hours(events)==3
    assert weekly_hours(events,datetime(2026,9,21))==2

def test_ai_disabled(client,monkeypatch):
    monkeypatch.setattr('app.requests.post',lambda *a,**k: pytest.fail('AI called while disabled'))
    login(client)
    assert post(client,'/ai-helper',{'question':'hi'}).status_code==200

def test_ai_permissions(client,app,monkeypatch):
    app.config['AI_ENABLED']=True
    captured=[]
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message':{'content':'test response'}}
    def fake(*a,**kw): captured.append(kw['json']); return Response()
    monkeypatch.setattr('app.requests.post',fake)
    login(client)
    assert post(client,'/ai-helper',{'question':'inventory?'}).status_code==200
    assert 'DEMO 195' not in captured[-1]['messages'][0]['content']
    post(client,'/logout');login(client,'manager')
    assert post(client,'/ai-helper',{'question':'inventory?'}).status_code==200
    assert 'DEMO 195' in captured[-1]['messages'][0]['content']

def test_ai_failure(client,app,monkeypatch):
    import requests
    app.config['AI_ENABLED']=True
    def fail(*a,**kw): raise requests.Timeout('internal-secret-address')
    monkeypatch.setattr('app.requests.post',fail)
    login(client)
    r=post(client,'/ai-helper',{'question':'hi'})
    assert r.status_code==200
    assert b'internal-secret-address' not in r.data

def test_demo_guard_and_production(app,client):
    app.config['DEMO_MODE']=False
    assert post(client,'/demo-login/manager').status_code==404
    with pytest.raises(RuntimeError):create_app({'PRODUCTION':True,'SECRET_KEY':None})

def test_headers(client):
    r=client.get('/')
    assert r.headers['X-Frame-Options']=='DENY'
    assert 'HttpOnly' in r.headers['Set-Cookie']
    assert 'SameSite=Lax' in r.headers['Set-Cookie']

def test_legacy_guard(tmp_path):
    path=tmp_path/'legacy.db'
    with sqlite3.connect(path) as db: db.execute('CREATE TABLE users(id INTEGER,password TEXT)')
    a=create_app({'TESTING':True,'DATABASE':str(path),'SECRET_KEY':'x'*40})
    r=a.test_cli_runner().invoke(args=['init-db'])
    assert r.exit_code!=0
    assert 'Legacy database' in r.output

def test_authenticated_csrf(client):
    login(client,'manager')
    assert client.post('/inventory',data={'tire_type':'X','quantity':'1'}).status_code==400
    assert client.post('/logout').status_code==400

def test_session_role_is_not_authority(client):
    login(client)
    with client.session_transaction() as session:
        session['role']='manager'
    assert client.get('/inventory').status_code==403

def test_report_isolation(client,app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',('other',generate_password_hash('long-password-example'),'worker'))
        db.execute("INSERT INTO work_sessions(username,action,timestamp) VALUES ('other','start','2025-01-01 03:00:00')")
    login(client)
    assert b'2025-01-01' not in client.get('/worker_report').data

def test_ai_limits_and_length(client,app,monkeypatch):
    app.config['AI_ENABLED']=True
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message':{'content':'answer'}}
    monkeypatch.setattr('app.requests.post',lambda *a,**k: Response())
    login(client)
    assert post(client,'/ai-helper',{'question':'x'*1001}).status_code==400
    for _ in range(5): assert post(client,'/ai-helper',{'question':'hi'}).status_code==200
    assert post(client,'/ai-helper',{'question':'hi'}).status_code==429

def test_demo_seed_refuses_overwrite(app):
    assert app.test_cli_runner().invoke(args=['seed-demo']).exit_code!=0

def test_sql_injection_login(client):
    assert post(client,'/login',{'username':"' OR 1=1 --",'password':'whatever'}).status_code==401

def test_account_command(app):
    r=app.test_cli_runner().invoke(args=['create-user','--username','new','--role','worker','--password','safe-testing-password'])
    assert r.exit_code==0,r.output
    with sqlite3.connect(app.config['DATABASE']) as db:
        value=db.execute("SELECT password_hash FROM users WHERE username='new'").fetchone()[0]
        assert value!='safe-testing-password'
        assert value.startswith('scrypt:')

def test_concurrent_clock_in(app):
    from concurrent.futures import ThreadPoolExecutor
    clients=[app.test_client(),app.test_client()]
    for c in clients: login(c)
    tokens=[token(c) for c in clients]
    def submit(i): return clients[i].post('/work',data={'action':'start','csrf_token':tokens[i]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit,[0,1]))==[302,409]
