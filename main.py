import os
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask import g  # global session-level object
from datetime import datetime
from types import SimpleNamespace
import db

N_INDEX_LIMIT = 100
N_RECENT_IN_STATS = 10

# REQUIRED ENV VARS
SESSION_SECRET = os.environ.get("SESSION_SECRET", "devkey")
MOON_READER_TOKEN = os.environ.get("SESSION_SECRET", "token not set")
PASSWORD = os.environ["PASSWORD"]

PUBLIC_ROUTES = [
    "check_login",
    "login",
    "logout",
    "index",
    "stats",
    "static",
    "mr_import",
]
assert "check_login" in PUBLIC_ROUTES

app = Flask(__name__)
app.secret_key = SESSION_SECRET
if app.secret_key == "devkey":
    print("WARNING: no secret key found, using default devkey")


@app.before_request
def check_if_logged():
    g.logged_in = session.get("logged_in", False)


@app.before_request
def require_auth():
    if request.endpoint not in PUBLIC_ROUTES and not session.get("logged_in"):
        return render_template("_login_modal.html")


@app.route("/check_login", methods=["POST"])
def check_login():
    if request.json.get("password") == PASSWORD:
        session["logged_in"] = True
        session.permanent = True
        return jsonify(success=True)
    return jsonify(success=False)


@app.route("/login")
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template(
        "_login_modal.html",
    )


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))


@app.route("/")
def index():
    """Home page showing all highlights with filtering options"""
    book_filter = request.args.get("book")
    favorites_only = request.args.get("favorites") == "1"
    random_sort = request.args.get("random") == "1"
    search_query = request.args.get("q")

    # Logged out restrictions -- just show last 20ish favorites
    if not g.logged_in:
        random_sort = 0
        favorites_only = 1
        book_filter = ""
        limit = None
    else:
        limit = N_INDEX_LIMIT

    highlights = db.get_all_highlights(
        book_filter,
        favorites_only,
        limit=limit,
        shuffle=random_sort,
        search_query=search_query,
    )
    books = db.get_all_books()

    return render_template(
        "index.html",
        highlights=highlights,
        books=books,
        current_book=book_filter,
        favorites_only=favorites_only,
        random=random_sort,
        search_query=search_query,
    )


@app.route("/review")
def review():
    """Page showing today's highlights to review"""
    highlights = db.get_highlights_for_review()
    return render_template("review.html", highlights=highlights)


@app.route("/add", methods=["GET", "POST"])
def add_highlight():
    """Form to manually add a new highlight"""
    quote_book_title = db.DEFAULT_QUOTE_BOOK_TITLE
    entry_type = request.form.get("entry_type", "book")

    if request.method == "POST":
        book_title = request.form.get("book_title", "").strip()
        if entry_type == "quote":
            book_title = quote_book_title
        elif not book_title:
            book_title = "Unknown"

        data = {
            "book_title": book_title,
            "highlight_text": request.form.get("highlight_text", ""),
            "author": request.form.get("author") or None,
            "note": request.form.get("note") or None,
            "favorite": bool(request.form.get("favorite")),
        }
        try:
            db.add_highlight(data)
            flash("Highlight added!")
            return redirect(url_for("index"))
        except Exception as e:
            flash(str(e))
    return render_template(
        "add_highlight.html",
        quote_default_title=quote_book_title,
        entry_type=entry_type,
    )


@app.route("/stats")
def stats():
    return render_template(
        "stats.html", stats=db.get_highlight_stats(N_RECENT_IN_STATS)
    )


@app.route("/highlight/<int:highlight_id>/<action>", methods=["GET", "POST"])
def highlight_action(highlight_id, action):
    """Handle favorite, delete, and restore actions on highlights"""

    highlight = db.get_highlight_by_id(highlight_id)
    if not highlight:
        return "", 404

    if action == "favorite":
        new_value = not bool(highlight["favorite"])
        db.update_highlight(highlight_id, "favorite", new_value)
        updated_highlight = SimpleNamespace(**highlight)
        updated_highlight.favorite = new_value
        return render_template("_favorite_button.html", highlight=updated_highlight)

    elif action == "delete":
        new_value = not bool(highlight["deleted"])
        db.update_highlight(highlight_id, "deleted", new_value)
        updated_highlight = SimpleNamespace(**highlight)
        updated_highlight.deleted = new_value
        return render_template_string(
            """
            {% from "_highlight_card.html" import highlight_card %}
            {{ highlight_card(highlight, show_all_actions=True) }}
        """,
            highlight=updated_highlight,
        )

    elif action == "edit_modal":
        updated_highlight = SimpleNamespace(**highlight)
        return render_template_string(
            """
            {% from "_edit_modal.html" import edit_modal %}
            {{ edit_modal(highlight) }}
            """,
            highlight=updated_highlight,
        )

    elif action == "edit":
        highlight_text = request.form.get("highlight_text")
        db.update_highlight(highlight_id, "highlight_text", highlight_text)

        updated_highlight = db.get_highlight_by_id(highlight_id)
        updated_highlight = SimpleNamespace(**updated_highlight)
        return render_template_string(
            """
            {% from "_highlight_card.html" import highlight_card %}
            {{ highlight_card(highlight, show_all_actions=True) }}
            """,
            highlight=updated_highlight,
        )

    else:
        app.logger.warning(f"Invalid action '{action}' for highlight {highlight_id}")
        return "", 400


@app.route("/book/<book_str>/<action>", methods=["POST"])
def book_action(book_str, action):
    """Handle renaming, deleting, and editing book author"""
    print("here")

    if action == "edit":
        db.rename_book(book_str, request.form.get("new_name"))
        return "", 200

    elif action == "edit_author":
        db.update_book_author(book_str, request.form.get("new_author"))
        return "", 200

    elif action == "delete":
        db.delete_book(book_str)
        print("deleted book")
        return "", 200

    else:
        app.logger.warning(f"Invalid action '{action}' for book {book_str}")
        return "", 400


@app.route("/mr-import", methods=["POST"])
def mr_import():
    """Import highlights from MoonReader with 'Readwise sync' function"""

    token = request.headers.get("Authorization", "Token").split("Token")[1].strip()
    if token != os.environ.get("MOON_READER_TOKEN"):
        print("Token does not match")
        return "", 500

    data = request.get_json()["highlights"][0]

    db.add_highlight(
        {
            "book_title": data["title"],
            "highlight_text": data["text"],
            "author": data["author"],
            "location": data["chapter"],
        }
    )

    return "", 200


@app.template_filter("str_to_date")
def str_to_date(value, format="%B, %Y"):
    if value:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime(format)
    return "Unknown date"


if __name__ == "__main__":
    app.run(debug=True, port=5002)
