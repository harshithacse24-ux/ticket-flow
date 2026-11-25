"""TicketFlow's lightweight local text classifier and knowledge-base matcher."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity


TRAINING = [
 ('Account/Login','forgot password reset password password reset login cannot login locked account login issue username password sign in'),
 ('Account/Login','unable to sign in login portal account locked forgot credentials reset credentials'),
 ('Network','wifi wi-fi internet network disconnected cannot connect network connection no internet'),
 ('Network','network slow connectivity issue campus wifi internet not working'),
 ('Hardware','laptop computer broken keyboard mouse monitor printer not responding hardware device power cable'),
 ('Hardware','screen black computer will not start hardware damaged device'),
 ('Hardware','laptop keyboard is broken mouse damaged monitor not working printer failure'),
 ('Hardware','physical computer hardware issue broken laptop device'),
 ('Software','application software app crash error installation install update program not working'),
 ('Software','software freezes application error cannot open app update failed'),
 ('Email','email mailbox mail account cannot send receive emails campus email'),
 ('Email','email not working inbox messages attachments email login'),
 ('Infrastructure','server outage portal down service unavailable server down all users'),
 ('Infrastructure','database server infrastructure system outage multiple people affected'),
 ('Account/Login','password reset cannot log in portal login page sign in credentials'),
 ('Network','campus wi-fi connection internet not available network disconnected'),
 ('Software','program application not opening software crashes update problem'),
 ('Hardware','broken physical device computer monitor printer mouse keyboard repair'),
 ('Email','email account messages sending receiving mail inbox issue'),
 ('Infrastructure','college service portal server unavailable outage multiple users'),
 ('Other','question help request general IT support miscellaneous issue')]
texts = [t for _,t in TRAINING]
labels = [c for c,_ in TRAINING]
vectorizer = TfidfVectorizer(ngram_range=(1,2),stop_words='english')
X = vectorizer.fit_transform(texts)
model = LogisticRegression(max_iter=1000,random_state=7)
model.fit(X,labels)
KB = [
 ('Account/Login','password reset forgot password account locked login','To reset your password, open the college portal login page and select “Forgot Password”. Follow the email verification steps. If the reset email does not arrive, contact the IT Help Desk.','Password Reset Guide'),
 ('Network','wifi wi-fi internet network connectivity cannot connect','Turn Wi-Fi off and on, confirm you are connecting to the official campus network, then forget the network and reconnect. If multiple users are affected, report the location to the Network Team.','Campus Wi-Fi Troubleshooting'),
 ('Software','software application app install update error crashing','Restart the application and your device. Check whether an update is available and confirm the application is approved for your device. Include the exact error message if the issue continues.','Software Troubleshooting'),
 ('Hardware','laptop computer keyboard mouse monitor printer device broken not working','Check the cable and power connection, then restart the device if safe. Do not open or repair college-owned equipment yourself. Send the device name and room number to the Hardware Team.','Hardware First Checks'),
 ('Email','email mailbox outlook gmail mail account sending receiving','Check your internet connection and mailbox storage. Verify the recipient and attachment size, then try again. If campus email access is blocked, contact the Email Support Team.','Email Troubleshooting'),
 ('Infrastructure','server outage down all users system unavailable portal outage','If a service is unavailable for multiple users, do not repeatedly retry. Record the service name and time observed. This ticket is routed to Infrastructure for investigation.','Service Outage Reporting')]
kb_vectorizer = TfidfVectorizer(stop_words='english')
kb_matrix = kb_vectorizer.fit_transform([keywords+' '+solution for _,keywords,solution,_ in KB])

def classify_ticket(text):
    row=vectorizer.transform([text])
    prediction=model.predict(row)[0]
    confidence=float(max(model.predict_proba(row)[0]))
    # Keep low confidence predictions from being over-trusted.
    if confidence < 0.20: prediction='Other'
    return prediction, confidence

def find_kb_solution(text, category):
    row=kb_vectorizer.transform([text])
    scores=cosine_similarity(row,kb_matrix)[0]
    idx=int(scores.argmax())
    if scores[idx] < 0.10: return None,None
    cat,_,solution,source=KB[idx]
    # Only return a solution if the article aligns with predicted category or a close match.
    if cat != category and scores[idx] < 0.24: return None,None
    return solution,source

def search_knowledge_base(text, category=None, top_k=3):
    row=kb_vectorizer.transform([text]); scores=cosine_similarity(row,kb_matrix)[0]
    results=[]
    for idx in scores.argsort()[::-1][:top_k]:
        score=float(scores[idx]); cat,keywords,solution,source=KB[int(idx)]
        if score<0.06 or (category and cat!=category and score<0.22): continue
        results.append({'category':cat,'keywords':keywords,'solution':solution,'source_title':source,'score':score})
    return results

def find_duplicate(text, threshold=0.72):
    """Find similar ticket text in the local DB; returns ticket id or None."""
    try:
        import sqlite3, os
        db_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'ticketflow.db')
        with sqlite3.connect(db_path) as db:
            rows=db.execute('SELECT id,title,description FROM tickets ORDER BY id DESC LIMIT 300').fetchall()
        if not rows: return None
        corpus=[text]+[r[1]+' '+r[2] for r in rows]
        vec=TfidfVectorizer(stop_words='english').fit_transform(corpus)
        scores=cosine_similarity(vec[0:1],vec[1:])[0]
        if scores.max() >= threshold:
            return int(rows[int(scores.argmax())][0])
    except Exception:
        return None
    return None
