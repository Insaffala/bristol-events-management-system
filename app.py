
from flask import Flask, render_template, request, session, redirect, url_for, send_file, make_response
from datetime import date, timedelta
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import io

from dbfunc import (
    get_events,
    get_filtered_events,
    get_all_categories,
    get_event_by_id,
    get_event_conditions,
    get_event_conditions_text,
    save_event_conditions_text,
    get_event_days,
    get_total_for_selected_days,
    check_login,
    create_user,
    user_already_booked,
    get_confirmed_booking_count,
    get_event_capacity,
    user_already_waiting,
    join_waiting_list,
    get_user_bookings,
    get_user_waiting_list,
    get_first_waiting_user,
    mark_waiting_as_promoted,
    create_promoted_booking,
    calculate_best_discount,
    create_booking_with_discount,
    create_booking_with_discount_and_days,
    get_booking_for_user,
    calculate_cancellation_charge,
    update_booking_to_cancelled,
    get_all_events_admin,
    get_all_venues,
    add_venue,
    admin_add_event,
    admin_delete_event,
    get_event_full_by_id,
    admin_update_event,
    get_all_users_admin,
    admin_update_user_role,
    admin_delete_user,
    update_user_password,
    verify_user_password,
    get_report_bookings_per_event,
    get_report_revenue_per_event,
    get_report_remaining_tickets,
    get_report_full,
    get_event_suitability,
    add_venue_with_image,
    update_venue,
    get_venue_by_id,
    delete_venue,
    can_reduce_event_price,
    reduce_event_price_if_allowed,
)

load_dotenv()

app = Flask(__name__)
# Security: keep the secret key outside source code in production.
app.secret_key = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_FOLDER = os.path.join("static", "img")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "avif", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def validate_input(value, field_name="Field", min_length=1, max_length=255, numeric=False, min_value=None):
    """Basic server-side validation for form data.
    This supports MO3 security: we reject empty, over-long, and invalid numeric input before database use.
    SQL injection is also reduced because all database functions use parameterised %s queries.
    """
    value = str(value or "").strip()
    if len(value) < min_length:
        return False, f"{field_name} is required."
    if len(value) > max_length:
        return False, f"{field_name} is too long."
    if numeric:
        try:
            number = float(value)
        except ValueError:
            return False, f"{field_name} must be a number."
        if min_value is not None and number < min_value:
            return False, f"{field_name} must be at least {min_value}."
    return True, ""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    return filename


def admin_only():
    return session.get("user_id") and session.get("role") == "admin"


def fallback_event_image(event):
    event_id = event.get("event_id") if isinstance(event, dict) else None
    mapping = {
        1: "hyppodrome2.jpg",
        2: "1.jpg",
        3: "paint.avif",
        4: "crochet-workshop.jpg",
        5: "BONFIRE.jpeg",
        6: "diwali.jpeg",
    }
    return mapping.get(event_id, "bristol-pic2.jpg")


@app.route("/")
def home():
    # Filters from URL
    search_term = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", "").strip()
    month = request.args.get("month", "").strip()
    free_only = request.args.get("free_only") in ["1", "on", "true"]

    # Use saved category ONLY if user did not submit category filter now
    if "category_id" not in request.args and not category_id:
        category_id = request.cookies.get("last_category", "").strip()

    # Get filtered events
    events = get_filtered_events(
        search_term=search_term,
        category_id=category_id,
        free_only=free_only,
        month=month
    )

    # Load dropdown + venue section
    categories = get_all_categories()
    venues = get_all_venues()

    response = make_response(render_template(
        "event.html",
        events=events,
        venues=venues,
        categories=categories,
        search_term=search_term,
        selected_category=category_id,
        selected_month=month,
        free_only=free_only
    ))

    # Optional cookie memory
    if request.cookies.get("cookie_consent") == "yes":

        # Save selected category
        if category_id:
            response.set_cookie(
                "last_category",
                category_id,
                max_age=60 * 60 * 24 * 365,
                samesite="Lax"
            )

        # If user selected All Categories -> remove old saved filter
        elif "category_id" in request.args:
            response.delete_cookie("last_category")

    return response

@app.route("/events")
def events():
    return redirect(url_for("home"))



@app.route("/event-detail/<int:event_id>")
def event_detail(event_id):
    event = get_event_by_id(event_id)
    message = request.args.get("message", "")

    if not event:
        return redirect(url_for("home"))

    days_until_event = (event["event_starting_date"] - date.today()).days

    booking_not_open_message = ""
    if days_until_event > 60:
        booking_not_open_message = (
            f"Bookings for this event are not open yet. "
            f"Please check back in {days_until_event - 60} day(s)."
        )

    confirmed_count = get_confirmed_booking_count(event_id)
    capacity = get_event_capacity(event_id)
    remaining_tickets = capacity - confirmed_count
    is_full = remaining_tickets <= 0
    conditions = get_event_conditions(event_id)
    event_days = get_event_days(event_id)

    return render_template(
        "event-detail.html",
        event=event,
        message=message or booking_not_open_message,
        remaining_tickets=remaining_tickets,
        is_full=is_full,
        conditions=conditions,
        conditions_text=get_event_conditions_text(event_id),
        suitability_text=get_event_suitability(event_id),
        event_days=event_days,
        active_page="events",
        fallback_event_image=fallback_event_image,
    )

@app.route("/book/<int:event_id>", methods=["POST"])
def book_event(event_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    event = get_event_by_id(event_id)

    if not event:
        return redirect(url_for("home"))

    if get_confirmed_booking_count(event_id) >= get_event_capacity(event_id):
        return redirect(url_for("event_detail", event_id=event_id, message="This event is fully booked. Please join the waiting list."))

    if user_already_booked(user_id, event_id):
        return redirect(url_for("event_detail", event_id=event_id, message="You already booked this event."))

    is_student = request.form.get("is_student") == "yes"
    selected_day_ids = request.form.getlist("selected_days")

    if selected_day_ids:
        original_price = get_total_for_selected_days(selected_day_ids)
    else:
        original_price = float(event["event_total_price"])

    discount_info = calculate_best_discount(
        event["event_starting_date"],
        float(original_price),
        is_student
    )

    session["pending_booking"] = {
        "event_id": event_id,
        "selected_day_ids": selected_day_ids,
        "original_price": float(original_price),
        "advance_percent": discount_info["advance_percent"],
        "student_percent": discount_info["student_percent"],
        "chosen_percent": discount_info["chosen_percent"],
        "discount_amount": discount_info["discount_amount"],
        "discount_type": discount_info["discount_type"],
        "final_price": discount_info["final_price"],
        "is_student": "yes" if is_student else "no"
    }

    return redirect(url_for("payment", event_id=event_id))

@app.route("/payment/<int:event_id>")
def payment(event_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    pending = session.get("pending_booking")

    if not pending or pending["event_id"] != event_id:
        return redirect(url_for("event_detail", event_id=event_id))

    event = get_event_by_id(event_id)

    if not event:
        return redirect(url_for("home"))

    return render_template(
        "payment.html",
        event=event,
        original_price=pending["original_price"],
        advance_percent=pending["advance_percent"],
        student_percent=pending["student_percent"],
        chosen_percent=pending["chosen_percent"],
        discount_amount=pending["discount_amount"],
        final_price=pending["final_price"],
        is_student=pending["is_student"]
    )

@app.route("/confirm-payment", methods=["POST"])
def confirm_payment():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    pending = session.get("pending_booking")

    if not pending:
        return redirect(url_for("home"))

    event_id = pending["event_id"]

    if user_already_booked(session["user_id"], event_id):
        session.pop("pending_booking", None)
        return redirect(url_for(
            "event_detail",
            event_id=event_id,
            message="You already booked this event."
        ))

    selected_day_ids = pending.get("selected_day_ids", [])

    if selected_day_ids:
        booking_id = create_booking_with_discount_and_days(
        session["user_id"],
        event_id,
        pending["final_price"],
        pending["discount_amount"],
        pending["discount_type"],
        selected_day_ids
    )
    else:
         booking_id = create_booking_with_discount(
        session["user_id"],
        event_id,
        pending["final_price"],
        pending["discount_amount"],
        pending["discount_type"]
    )
    session.pop("pending_booking", None)

    return redirect(url_for(
        "booking_receipt",
        booking_id=booking_id,
        event_id=event_id,
        original_price=pending["original_price"],
        advance_percent=pending["advance_percent"],
        student_percent=pending["student_percent"],
        chosen_percent=pending["chosen_percent"],
        discount_amount=pending["discount_amount"],
        final_price=pending["final_price"],
        is_student=pending["is_student"]
    ))


@app.route("/booking-receipt/<int:booking_id>/<int:event_id>")
def booking_receipt(booking_id, event_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    event = get_event_by_id(event_id)
    return render_template(
        "booking_receipt.html",
        booking_id=booking_id,
        event=event,
        original_price=request.args.get("original_price"),
        advance_percent=request.args.get("advance_percent"),
        student_percent=request.args.get("student_percent"),
        chosen_percent=request.args.get("chosen_percent"),
        discount_amount=request.args.get("discount_amount"),
        final_price=request.args.get("final_price"),
        is_student=request.args.get("is_student"),
        active_page="wallet",
        fallback_event_image=fallback_event_image,
    )


@app.route("/booking-receipt/<int:booking_id>/<int:event_id>/download")
def download_receipt_pdf(booking_id, event_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    event = get_event_by_id(event_id)
    original_price = request.args.get("original_price", "")
    final_price = request.args.get("final_price", "")
    discount_amount = request.args.get("discount_amount", "")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        pdf = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        # Professional receipt header
        pdf.setFillColor(colors.HexColor("#0B3558"))
        pdf.rect(0, height - 38 * mm, width, 38 * mm, fill=True, stroke=False)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(22 * mm, height - 18 * mm, "Bristol Community Events")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(22 * mm, height - 27 * mm, "Official booking receipt / invoice")

        y = height - 52 * mm
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(22 * mm, y, f"Booking ID: {booking_id}")
        pdf.setFont("Helvetica", 11)
        y -= 9 * mm
        pdf.drawString(22 * mm, y, f"Event: {event['event_name']}")
        y -= 7 * mm
        pdf.drawString(22 * mm, y, f"Venue: {event['venue_name']}")
        y -= 7 * mm
        pdf.drawString(22 * mm, y, f"Date: {event['event_starting_date']}")

        y -= 14 * mm
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(22 * mm, y, "Price breakdown")
        y -= 8 * mm
        rows = [
            ("Original price", f"£{original_price}"),
            ("Advance discount", f"{request.args.get('advance_percent', '0')}%"),
            ("Student discount", f"{request.args.get('student_percent', '0')}%"),
            ("Chosen discount", f"{request.args.get('chosen_percent', '0')}%"),
            ("Discount amount", f"£{discount_amount}"),
            ("Final total", f"£{final_price}"),
        ]
        for label, value in rows:
            pdf.setFont("Helvetica", 11)
            pdf.drawString(25 * mm, y, label)
            pdf.drawRightString(170 * mm, y, value)
            y -= 8 * mm
        pdf.line(22 * mm, y + 4 * mm, 175 * mm, y + 4 * mm)
        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawString(22 * mm, 25 * mm, "Thank you for booking with BCE. Students must bring a valid student ID if a student discount was used.")
        pdf.showPage(); pdf.save(); buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"receipt_{booking_id}.pdf", mimetype="application/pdf")
    except Exception:
        content = (
            f"Bristol Community Events - Booking Receipt\n\n"
            f"Booking ID: {booking_id}\n"
            f"Event: {event['event_name']}\n"
            f"Venue: {event['venue_name']}\n"
            f"Start Date: {event['event_starting_date']}\n"
            f"Original Price: £{original_price}\n"
            f"Discount Amount: £{discount_amount}\n"
            f"Final Total: £{final_price}\n"
        )
        response = make_response(content)
        response.headers["Content-Type"] = "text/plain"
        response.headers["Content-Disposition"] = f"attachment; filename=receipt_{booking_id}.txt"
        return response


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ok_user, msg_user = validate_input(username, "Username", 3, 64)
        ok_pass, msg_pass = validate_input(password, "Password", 1, 128)
        if not ok_user or not ok_pass:
            message = msg_user or msg_pass
            return render_template("login.html", message=message, active_page="login")
        user = check_login(username, password)
        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        message = "Invalid username or password."
    return render_template("login.html", message=message, active_page="login")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ok_user, msg_user = validate_input(username, "Username", 3, 64)
        ok_pass, msg_pass = validate_input(password, "Password", 1, 128)
        if not ok_user or not ok_pass:
            message = msg_user or msg_pass
            return render_template("signup.html", message=message, active_page="signup")
        try:
            create_user(username, password)
            message = "Account created successfully. You can now log in."
        except Exception:
            message = "This username already exists. Please choose another one."
    return render_template("signup.html", message=message, active_page="signup")


@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    message = ""
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        ok_pass, msg_pass = validate_input(new_password, "New password", 6, 128)
        if not ok_pass:
            message = msg_pass
        elif new_password != confirm_password:
            message = "New passwords do not match."
        elif not verify_user_password(session["user_id"], current_password):
            message = "Current password is incorrect."
        else:
            update_user_password(session["user_id"], new_password)
            message = "Password updated successfully."
    return render_template("change_password.html", message=message, active_page="wallet")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", active_page="privacy")


@app.route("/join-waiting-list/<int:event_id>", methods=["POST"])
def add_to_waiting_list(event_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    event = get_event_by_id(event_id)
    if not event:
        return redirect(url_for("home"))
    if user_already_booked(user_id, event_id):
        return redirect(url_for("event_detail", event_id=event_id, message="You already have a confirmed booking."))
    if user_already_waiting(user_id, event_id):
        return redirect(url_for("event_detail", event_id=event_id, message="You are already on the waiting list."))
    join_waiting_list(user_id, event_id)
    return redirect(url_for("event_detail", event_id=event_id, message="You have been added to the waiting list."))


@app.route("/my_wallet")
def my_wallet():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    all_bookings = get_user_bookings(user_id)
    waiting_entries = get_user_waiting_list(user_id)
    message = request.args.get("message", "")

    today = date.today()

    current_bookings = []
    past_bookings = []

    for booking in all_bookings:
        if booking["booking_status"] == "confirmed" and booking["event_ending_date"] >= today:
            current_bookings.append(booking)
        else:
            past_bookings.append(booking)

    return render_template(
        "my_wallet.html",
        current_bookings=current_bookings,
        past_bookings=past_bookings,
        waiting_entries=waiting_entries,
        message=message
    )

@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_user_booking(booking_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user_id = session["user_id"]
    booking = get_booking_for_user(booking_id, user_id)
    if not booking:
        return redirect(url_for("my_wallet", message="Booking not found."))
    if booking["booking_status"] != "confirmed":
        return redirect(url_for("my_wallet", message="This booking is already cancelled."))

    charge_info = calculate_cancellation_charge(booking["total_price"], booking["event_starting_date"])
    success = update_booking_to_cancelled(booking_id, user_id, charge_info["charge_amount"], charge_info["charge_percent"])
    if not success:
        return redirect(url_for("my_wallet", message="Unable to cancel this booking."))

    event_id = booking["event_id"]
    waiting_user = get_first_waiting_user(event_id)
    if waiting_user:
        event = get_event_by_id(event_id)
        if event:
            create_promoted_booking(waiting_user["user_id"], event_id, event["event_total_price"])
            mark_waiting_as_promoted(waiting_user["wait_id"])

    if charge_info["charge_percent"] == 0:
        message = "Booking cancelled successfully. No cancellation charge applied."
    elif charge_info["charge_percent"] == 40:
        message = f"Booking cancelled successfully. 40% cancellation charge applied (£{charge_info['charge_amount']})."
    else:
        message = f"Booking cancelled successfully. 100% cancellation charge applied (£{charge_info['charge_amount']})."
    return redirect(url_for("my_wallet", message=message))


@app.route("/admin")
def admin_dashboard():
    if not admin_only():
        return redirect(url_for("home"))
    events = get_all_events_admin()
    venues = get_all_venues()
    categories = get_all_categories()
    message = request.args.get("message", "")
    reduction_status = {event["event_id"]: can_reduce_event_price(event["event_id"]) for event in events}
    return render_template("admin_dashboard.html", events=events, venues=venues, categories=categories,
                           message=message, active_page="admin", fallback_event_image=fallback_event_image,
                           reduction_status=reduction_status)


@app.route("/admin/add-event", methods=["POST"])
def admin_add_event_route():
    if not admin_only():
        return redirect(url_for("home"))
    event_name = request.form["event_name"]
    event_starting_date = request.form["event_starting_date"]
    event_ending_date = request.form["event_ending_date"]
    event_total_price = request.form["event_total_price"]
    venue_id = request.form["venue_id"]
    booking_deadline = request.form["booking_deadline"]
    event_description = request.form["event_description"]
    category_id = request.form["category_id"]
    conditions_text = request.form.get("event_conditions_text", "")
    image_file = request.files.get("event_image_file")
    saved_filename = save_uploaded_image(image_file) or fallback_event_image({"event_id": None})
    ok_name, msg_name = validate_input(event_name, "Event name", 3, 120)
    ok_price, msg_price = validate_input(event_total_price, "Event price", 1, 20, numeric=True, min_value=0)
    ok_desc, msg_desc = validate_input(event_description, "Event description", 5, 2000)
    if not (ok_name and ok_price and ok_desc):
        return redirect(url_for("admin_dashboard", message=msg_name or msg_price or msg_desc))
    try:
        event_id = admin_add_event(event_name, event_starting_date, event_ending_date, event_total_price,
                                   venue_id, booking_deadline, event_description, saved_filename, category_id)
        save_event_conditions_text(event_id, conditions_text)
        return redirect(url_for("admin_dashboard", message="Event added successfully."))
    except Exception as e:
        return redirect(url_for("admin_dashboard", message=f"Unable to add event. {e}"))


@app.route("/admin/edit-event/<int:event_id>")
def admin_edit_event_page(event_id):
    if not admin_only():
        return redirect(url_for("home"))
    event = get_event_full_by_id(event_id)
    venues = get_all_venues(); categories = get_all_categories()
    if not event:
        return redirect(url_for("admin_dashboard", message="Event not found."))
    return render_template("admin_edit_event.html", event=event, venues=venues, categories=categories,
                           event_conditions_text=get_event_conditions_text(event_id),
                           active_page="admin")


@app.route("/admin/update-event/<int:event_id>", methods=["POST"])
def admin_update_event_route(event_id):
    if not admin_only():
        return redirect(url_for("home"))
    event = get_event_full_by_id(event_id)
    if not event:
        return redirect(url_for("admin_dashboard", message="Event not found."))
    event_name = request.form["event_name"]
    event_starting_date = request.form["event_starting_date"]
    event_ending_date = request.form["event_ending_date"]
    event_total_price = request.form["event_total_price"]
    venue_id = request.form["venue_id"]
    booking_deadline = request.form["booking_deadline"]
    event_description = request.form["event_description"]
    category_id = request.form["category_id"]
    conditions_text = request.form.get("event_conditions_text", "")
    image_file = request.files.get("event_image_file")
    saved_filename = save_uploaded_image(image_file) or event.get("event_image") or fallback_event_image(event)
    ok_name, msg_name = validate_input(event_name, "Event name", 3, 120)
    ok_price, msg_price = validate_input(event_total_price, "Event price", 1, 20, numeric=True, min_value=0)
    ok_desc, msg_desc = validate_input(event_description, "Event description", 5, 2000)
    if not (ok_name and ok_price and ok_desc):
        return redirect(url_for("admin_dashboard", message=msg_name or msg_price or msg_desc))
    try:
        admin_update_event(event_id, event_name, event_starting_date, event_ending_date, event_total_price,
                           venue_id, booking_deadline, event_description, saved_filename, category_id)
        save_event_conditions_text(event_id, conditions_text)
        return redirect(url_for("admin_dashboard", message="Event updated successfully."))
    except Exception as e:
        return redirect(url_for("admin_dashboard", message=f"Unable to update event. {e}"))


@app.route("/admin/delete-event/<int:event_id>", methods=["POST"])
def admin_delete_event_route(event_id):
    if not admin_only():
        return redirect(url_for("home"))
    success = admin_delete_event(event_id)
    return redirect(url_for("admin_dashboard", message="Event deleted successfully." if success else "Unable to delete event."))


@app.route("/admin/reduce-price/<int:event_id>", methods=["POST"])
def admin_reduce_price_route(event_id):
    if not admin_only():
        return redirect(url_for("home"))
    result = reduce_event_price_if_allowed(event_id)
    return redirect(url_for("admin_dashboard", message=result["message"]))

@app.route("/admin/reports")
def admin_reports():
    if not admin_only():
        return redirect(url_for("home"))
    report = get_report_full()
    return render_template("admin_reports.html", report=report, active_page="reports")


@app.route("/admin/venues", methods=["GET", "POST"])
def admin_venues():
    if not admin_only():
        return redirect(url_for("home"))
    message = request.args.get("message", "")
    if request.method == "POST":
        try:
            ok_name, msg_name = validate_input(request.form.get("venue_name"), "Venue name", 3, 120)
            ok_address, msg_address = validate_input(request.form.get("address"), "Address", 3, 255)
            ok_capacity, msg_capacity = validate_input(request.form.get("capacity"), "Capacity", 1, 10, numeric=True, min_value=1)
            ok_suitability, msg_suitability = validate_input(request.form.get("suitability"), "Suitability", 3, 255)
            if not (ok_name and ok_address and ok_capacity and ok_suitability):
                raise ValueError(msg_name or msg_address or msg_capacity or msg_suitability)
            image_file = request.files.get("venue_image_file")
            saved_image = save_uploaded_image(image_file)
            add_venue_with_image(
                request.form["venue_name"],
                request.form["address"],
                request.form["capacity"],
                saved_image,
                request.form.get("suitability", "")
            )
            return redirect(url_for("admin_venues", message="Venue added successfully."))
        except Exception as e:
            message = f"Unable to add venue. {e}"
    return render_template("admin_venues.html", venues=get_all_venues(), message=message, active_page="venues")


@app.route("/admin/edit-venue/<int:venue_id>", methods=["GET", "POST"])
def admin_edit_venue(venue_id):
    if not admin_only():
        return redirect(url_for("home"))
    venue = get_venue_by_id(venue_id)
    if not venue:
        return redirect(url_for("admin_venues", message="Venue not found."))
    if request.method == "POST":
        try:
            ok_name, msg_name = validate_input(request.form.get("venue_name"), "Venue name", 3, 120)
            ok_address, msg_address = validate_input(request.form.get("address"), "Address", 3, 255)
            ok_capacity, msg_capacity = validate_input(request.form.get("capacity"), "Capacity", 1, 10, numeric=True, min_value=1)
            ok_suitability, msg_suitability = validate_input(request.form.get("suitability"), "Suitability", 3, 255)
            if not (ok_name and ok_address and ok_capacity and ok_suitability):
                raise ValueError(msg_name or msg_address or msg_capacity or msg_suitability)
            image_file = request.files.get("venue_image_file")
            saved_image = save_uploaded_image(image_file) or venue.get("venue_image")
            update_venue(
                venue_id,
                request.form["venue_name"],
                request.form["address"],
                request.form["capacity"],
                saved_image,
                request.form.get("suitability", "")
            )
            return redirect(url_for("admin_venues", message="Venue updated successfully."))
        except Exception as e:
            return redirect(url_for("admin_venues", message=f"Unable to update venue. {e}"))
    return render_template("admin_edit_venue.html", venue=venue, active_page="venues")


@app.route("/admin/delete-venue/<int:venue_id>", methods=["POST"])
def admin_delete_venue_route(venue_id):
    if not admin_only():
        return redirect(url_for("home"))
    try:
        delete_venue(venue_id)
        return redirect(url_for("admin_venues", message="Venue deleted. Events using it now have no venue assigned."))
    except Exception as e:
        return redirect(url_for("admin_venues", message=f"Cannot delete venue: {e}"))


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if not admin_only():
        return redirect(url_for("home"))
    message = ""
    if request.method == "POST":
        action = request.form.get("action")
        uid = request.form.get("user_id")

        if action == "role":
            role = request.form.get("role")
            if role not in ("standard", "admin"):
                message = "Invalid role selected."
            else:
                admin_update_user_role(uid, role)
                message = "User role updated."

        elif action == "password":
            new_password = request.form.get("new_password", "")
            ok_pass, msg_pass = validate_input(new_password, "New password", 6, 128)
            if not ok_pass:
                message = msg_pass
            else:
                update_user_password(uid, new_password)
                message = "User password updated."

        elif action == "delete":
            # Admin feature required by the brief: admin can remove end-user details.
            # The current logged-in admin is protected so they cannot accidentally delete their own account.
            try:
                uid_int = int(uid)
            except (TypeError, ValueError):
                message = "Invalid user selected."
            else:
                if uid_int == session.get("user_id"):
                    message = "You cannot delete your own logged-in admin account."
                else:
                    result = admin_delete_user(uid_int)
                    message = result["message"]

    return render_template("admin_users.html", users=get_all_users_admin(), message=message, active_page="admin")

@app.route("/accept-cookies", methods=["POST"])
def accept_cookies():
    response = make_response(redirect(request.referrer or url_for("home")))
    response.set_cookie(
        "cookie_consent",
        "yes",
        max_age=60 * 60 * 24 * 365
    )
    return response


@app.route("/reject-cookies", methods=["POST"])
def reject_cookies():
    response = make_response(redirect(request.referrer or url_for("home")))
    response.set_cookie(
        "cookie_consent",
        "no",
        max_age=60 * 60 * 24 * 365
    )
    response.delete_cookie("last_category")
    return response

@app.route("/reset-cookies")
def reset_cookies():
    response = make_response(redirect(url_for("home")))
    response.delete_cookie("cookie_consent")
    response.delete_cookie("last_category")
    return response

if __name__ == "__main__":
    app.run(host=os.environ.get("FLASK_HOST", "127.0.0.1"), port=int(os.environ.get("FLASK_PORT", "5010")), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")