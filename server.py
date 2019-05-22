from flask import Flask # 1.0.2
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
import json
import os
import datetime
from hashlib import sha256
from colorama import init # 0.4.1
from colorama import Fore
from threading import Timer
from gfqg import Document

# create flask app
app = Flask(__name__)

# init colorama, reset coloring on each print
init(autoreset=True)

@app.after_request
def after_request(response):
    """
    Enables CORS to allow AJAX requests from the webpage
    """

    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response

@app.route("/", methods=["GET"])
def default():
    """
    Default landing page
    Allows users to input their text to be processed
    """

    log("Received request for default page")
    return render_template("default.html")

@app.route("/generate", methods=["GET"])
def redirect_to_default():
    """
    Redirects users to main page if they make a GET request to /generate
    Generate should only be POSTed to
    """

    log("Received GET request for /generate, returning to default page")
    return redirect(url_for("default"))

"""
{
    "session_id": {
        "questions": [
            ("question", "answer")
        ],
        "current_question": index of last question that was sent as a form,
        "timer": <datetime object representing when data should be deleted>
    }
}
"""
data = dict()
@app.route("/generate", methods=["POST"])
def generate():
    """
    Accepts raw text data and creates questions
    Saves data with session id
    """

    global data

    log("Received request to generate questions")

    session_id = get_hash()
    log("Created session id", session_id=session_id)

    # make questions
    raw_data = str(request.form.get("data"))
    questions = Document(raw_data).format_questions()
    log("Created questions", questions, session_id=session_id)

    # store data
    data[session_id] = {
        "questions": questions,
        "current_question": 0
    }
    # timer to delete data
    reset_timer(session_id)

    log("Redirecting to questions page to begin questions", session_id=session_id)
    return(redirect(url_for("questions", session_id=session_id)))

@app.route("/questions", methods=["GET"])
def questions():
    """
    Each request is requesting a new question
    Generates all past questions and current question to send back
    """

    global data

    session_id = request.args.get("session_id")

    log("Received request for new questions", session_id=session_id)

    if session_id in data:
        # reset timer because they are active
        reset_timer(session_id)

        # check if there are more questions
        if data[session_id]["current_question"] >= len(data[session_id]["questions"]):
            has_more_questions = False
        else:
            has_more_questions = True

        # questions that have been answered to be redisplayed
        successful_questions = data[session_id]["questions"][:data[session_id]["current_question"]]
        
        # current question to be asked
        if has_more_questions:
            current_question = data[session_id]["questions"][data[session_id]["current_question"]]
        else:
            current_question = None

        # increment current question for next cycle
        data[session_id]["current_question"] = data[session_id]["current_question"] + 1
        
        if has_more_questions:
            log("Sending question", current_question, session_id=session_id)
        else:
            log("No more questions, sending questions finished message", session_id=session_id)
        return render_template(
            "questions.html", 
            successful_questions=successful_questions,
            current_question=current_question,
            has_more_questions=has_more_questions,
            session_id=session_id
        )
    else:
        # we dont have them at all (never made questions or it timed out and got deleted)
        log("No available questions (session id not found, timed out?), returning to home page")
        return redirect(url_for("default"))

def get_hash():
    """
    Returns hash for current user based on IP address and current time
    Used as user identifier
    """

    # put ip and date together
    ip = str(request.remote_addr)
    time = str(datetime.datetime.now())
    to_hash = (ip + time).encode()

    # sha256 hash
    h = sha256()
    h.update(to_hash)
    return h.hexdigest()

def reset_timer(session_id):
    """
    Resets (or adds, if it does not exist) a timer to delete a user's data
        after 10 minutes (prevents unused memory buildup)
    """

    global data
    # length of deletion timer (minutes)
    TIMER_LENGTH = 10

    # cancel last timer if there is one
    if session_id in data and "timer" in data[session_id]:
        data[session_id]["timer"].cancel()

    # make new timer
    data[session_id]["timer"] = Timer(60 * TIMER_LENGTH, delete_questions, args=[session_id])
    data[session_id]["timer"].start()
    log("Setting timer to", str(datetime.datetime.now() + datetime.timedelta(minutes=TIMER_LENGTH)), session_id=session_id)

def delete_questions(session_id):
    """
    Deletes questions for an IP address
    Intended to be used by timer
    """

    global data

    if session_id in data:
        log("Deleting data", session_id=session_id)
        del data[session_id]

def log(*args, session_id=None):
    """
    Session_id - session id
    Prints a message in yellow in format [current time, session_id] message
    """

    # construct message from args
    message = ""
    for arg in args:
        message += str(arg) + " "
    
    # print in yellow color
    # [current time, session_id] message
    print(Fore.YELLOW + "[%s, %s] %s" % (str(datetime.datetime.now()), str(session_id), message))

if __name__ == "__main__":
    # server start
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)