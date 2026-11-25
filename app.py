
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os, time
from datetime import datetime
from ml_engine import classify_ticket, find_kb_solution, find_duplicate, search_knowledge_base
from ai_assistant import generate_ai_response, ai_is_configured
BASE_DIR=os.path.dirname(os.path.abspath(__file__)); DB_PATH=os.path.join(BASE_DIR,'ticketflow.db')
app=Flask(__name__); app.secret_key=os.environ.get('FLASK_SECRET_KEY','ticketflow-demo-key')

def get_db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, requester TEXT NOT NULL, email TEXT,
        title TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL,
        priority TEXT NOT NULL, status TEXT NOT NULL, assigned_team TEXT NOT NULL,
        solution TEXT, kb_source TEXT, duplicate_of INTEGER, created_at TEXT NOT NULL,
        resolved_at TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, keywords TEXT,
        solution TEXT NOT NULL, source_title TEXT NOT NULL)''')
        if db.execute('SELECT COUNT(*) FROM knowledge_base').fetchone()[0]==0:
            db.executemany('INSERT INTO knowledge_base(category,keywords,solution,source_title) VALUES(?,?,?,?)',[
            ('Account/Login','password reset forgot password account locked login','To reset your password, open the college portal login page and select “Forgot Password”. Follow email verification. If the reset email does not arrive, contact IT Help Desk.','Password Reset Guide'),
            ('Network','wifi wi-fi internet network connectivity cannot connect','Turn Wi-Fi off and on, confirm the official campus network, then forget and reconnect. If multiple users are affected, report location to Network Team.','Campus Wi-Fi Troubleshooting'),
            ('Software','software application app install update error crashing','Restart the application and device. Check for updates and confirm the app is approved. Include the exact error if it continues.','Software Troubleshooting'),
            ('Hardware','laptop computer keyboard mouse monitor printer device broken not working','Check cables and power, restart if safe. Do not open college equipment yourself. Send device name and room to Hardware Team.','Hardware First Checks'),
            ('Email','email mailbox outlook gmail mail account sending receiving','Check internet and mailbox storage. Verify recipient and attachment size. If campus email is blocked, contact Email Support.','Email Troubleshooting'),
            ('Infrastructure','server outage down all users system unavailable portal outage','If multiple users are affected, do not repeatedly retry. Record service and time observed. Routed to Infrastructure for investigation.','Service Outage Reporting')])
        db.execute('CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY,session_id TEXT,role TEXT,message TEXT,created_at TEXT)')
init_db()
def team_for(cat):
    return {'Network':'Network Team','Hardware':'Hardware Team','Software':'Software Support','Account/Login':'Account Support','Email':'Email Support','Infrastructure':'Infrastructure Team','Other':'IT Help Desk'}.get(cat,'IT Help Desk')
def priority_for(text,cat):
    t=text.lower()
    if any(w in t for w in ['server down','outage','everyone','whole college','critical','all users']): return 'Critical'
    if any(w in t for w in ['urgent','deadline','exam','cannot work','not working','blocked','unable to access']): return 'High'
    if cat in ('Network','Hardware','Infrastructure'): return 'High'
    if any(w in t for w in ['slow','intermittent','sometimes']): return 'Medium'
    return 'Low'
@app.route('/')
def dashboard():
    with get_db() as db:
        total=db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
        resolved=db.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Resolved','Auto-resolved')").fetchone()[0]
        pending=db.execute("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('Resolved','Auto-resolved')").fetchone()[0]
        critical=db.execute("SELECT COUNT(*) FROM tickets WHERE priority='Critical'").fetchone()[0]
        auto=db.execute("SELECT COUNT(*) FROM tickets WHERE status='Auto-resolved'").fetchone()[0]
        rows=db.execute('SELECT * FROM tickets ORDER BY id DESC LIMIT 8').fetchall()
        cats=db.execute('SELECT category,COUNT(*) n FROM tickets GROUP BY category ORDER BY n DESC').fetchall()
        pri=db.execute('SELECT priority,COUNT(*) n FROM tickets GROUP BY priority').fetchall()
        avg=db.execute("SELECT AVG((julianday(resolved_at)-julianday(created_at))*1440) FROM tickets WHERE resolved_at IS NOT NULL").fetchone()[0]
    stats=dict(total=total,resolved=resolved,pending=pending,critical=critical,auto=auto,auto_rate=round(auto/total*100,1) if total else 0,avg_minutes=round(avg,1) if avg else 0)
    return render_template('dashboard.html',stats=stats,tickets=rows,categories=cats,priorities=pri,ai_enabled=ai_is_configured())
@app.route('/new',methods=['GET','POST'])
def new_ticket():
    if request.method=='POST':
        name=request.form.get('requester','').strip(); email=request.form.get('email','').strip()
        title=request.form.get('title','').strip(); desc=request.form.get('description','').strip()
        if not name or not title or not desc:
            flash('Name, title and description are required.','danger'); return render_template('new_ticket.html',ai_enabled=ai_is_configured())
        start=time.perf_counter(); full=title+' '+desc; cat,conf=classify_ticket(full); priority=priority_for(full,cat)
        sol,src=find_kb_solution(full,cat); dup=find_duplicate(full)
        ai_sol=None
        if ai_is_configured():
            ai_sol,_=generate_ai_response(full,search_knowledge_base(full,cat),task='ticket_solution')
        status='Auto-resolved' if sol and priority not in ('Critical','High') and conf>=.20 else 'Open'
        team='Auto-resolution Agent' if status=='Auto-resolved' else team_for(cat)
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as db:
            cur=db.execute('INSERT INTO tickets(requester,email,title,description,category,priority,status,assigned_team,solution,kb_source,duplicate_of,created_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(name,email,title,desc,cat,priority,status,team,sol if status=='Auto-resolved' else None,src if status=='Auto-resolved' else None,dup,now,now if status=='Auto-resolved' else None))
            tid=cur.lastrowid
        return render_template('ticket_result.html',ticket_id=tid,category=cat,confidence=round(conf*100,1),priority=priority,status=status,assigned=team,solution=sol if status=='Auto-resolved' else None,source=src if status=='Auto-resolved' else None,duplicate=dup,elapsed_ms=round((time.perf_counter()-start)*1000,1),ai_solution=ai_sol,ai_enabled=ai_is_configured())
    return render_template('new_ticket.html',ai_enabled=ai_is_configured())
@app.route('/tickets')
def tickets():
    s=request.args.get('status','')
    with get_db() as db: rows=db.execute('SELECT * FROM tickets WHERE status=? ORDER BY id DESC',(s,)).fetchall() if s else db.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    return render_template('tickets.html',tickets=rows,selected=s)
@app.route('/ticket/<int:tid>')
def ticket_detail(tid):
    with get_db() as db: ticket=db.execute('SELECT * FROM tickets WHERE id=?',(tid,)).fetchone()
    if not ticket: flash('Ticket not found.','warning'); return redirect(url_for('tickets'))
    return render_template('ticket_detail.html',ticket=ticket,ai_enabled=ai_is_configured())
@app.route('/ticket/<int:tid>/status',methods=['POST'])
def update_status(tid):
    s=request.form.get('status')
    if s not in ('Open','In Progress','Resolved'): flash('Invalid status.','danger'); return redirect(url_for('ticket_detail',tid=tid))
    resolved=datetime.now().strftime('%Y-%m-%d %H:%M:%S') if s=='Resolved' else None
    with get_db() as db:
        if not db.execute('SELECT 1 FROM tickets WHERE id=?',(tid,)).fetchone(): flash('Ticket not found.','warning'); return redirect(url_for('tickets'))
        db.execute('UPDATE tickets SET status=?,resolved_at=? WHERE id=?',(s,resolved,tid))
    flash('Status updated.','success'); return redirect(url_for('ticket_detail',tid=tid))
@app.route('/knowledge')
def knowledge():
    with get_db() as db: articles=db.execute('SELECT * FROM knowledge_base ORDER BY category').fetchall()
    return render_template('knowledge.html',articles=articles)
@app.route('/assistant',methods=['GET','POST'])
def assistant():
    sid=request.cookies.get('tf_chat_session') or os.urandom(12).hex()
    if request.method=='POST':
        msg=request.form.get('message','').strip()
        if msg:
            with get_db() as db:
                hist=db.execute('SELECT role,message FROM chat_messages WHERE session_id=? ORDER BY id DESC LIMIT 10',(sid,)).fetchall()
                articles=search_knowledge_base(msg,top_k=3)
            answer,mode=generate_ai_response(msg,articles,history=list(reversed(hist)),task='chat')
            now=datetime.now().isoformat(timespec='seconds')
            with get_db() as db:
                db.execute('INSERT INTO chat_messages(session_id,role,message,created_at) VALUES(?,?,?,?)',(sid,'user',msg,now))
                db.execute('INSERT INTO chat_messages(session_id,role,message,created_at) VALUES(?,?,?,?)',(sid,'assistant',answer,now))
        return redirect(url_for('assistant'))
    with get_db() as db: messages=db.execute('SELECT role,message FROM chat_messages WHERE session_id=? ORDER BY id',(sid,)).fetchall()
    response=app.make_response(render_template('assistant.html',messages=messages,ai_enabled=ai_is_configured()))
    response.set_cookie('tf_chat_session',sid,httponly=True,samesite='Lax'); return response
@app.route('/assistant/clear',methods=['POST'])
def clear_chat():
    sid=request.cookies.get('tf_chat_session')
    if sid:
        with get_db() as db: db.execute('DELETE FROM chat_messages WHERE session_id=?',(sid,))
    return redirect(url_for('assistant'))
@app.route('/seed-demo')
def seed_demo():
    examples=[('Asha','asha@example.edu','Forgot my portal password','I forgot my password and cannot login to the college portal.'),('Ravi','ravi@example.edu','WiFi issue in lab','Wi-Fi is not working in lab 2 and I cannot connect.'),('Maya','maya@example.edu','Printer is not working','The printer in the department is not responding.'),('Kiran','kiran@example.edu','Campus email problem','I cannot send email from my campus account.'),('Nisha','nisha@example.edu','Portal server down','The portal server is down for everyone in our class.')]
    with get_db() as db:
        for name,email,title,desc in examples:
            if db.execute('SELECT 1 FROM tickets WHERE title=? AND requester=?',(title,name)).fetchone(): continue
            cat,conf=classify_ticket(title+' '+desc); pr=priority_for(title+' '+desc,cat); sol,src=find_kb_solution(title+' '+desc,cat)
            status='Auto-resolved' if sol and pr not in ('Critical','High') and conf>=.2 else 'Open'; team='Auto-resolution Agent' if status=='Auto-resolved' else team_for(cat); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.execute('INSERT INTO tickets(requester,email,title,description,category,priority,status,assigned_team,solution,kb_source,created_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(name,email,title,desc,cat,pr,status,team,sol if status=='Auto-resolved' else None,src if status=='Auto-resolved' else None,now,now if status=='Auto-resolved' else None))
    flash('Demo tickets added; duplicates skipped.','success'); return redirect(url_for('dashboard'))
if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
