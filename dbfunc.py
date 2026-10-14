import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"]
    )


def get_events():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            e.event_id,
            e.event_name,
            e.event_starting_date,
            e.event_total_price,
            e.event_description,
            e.event_image,
            c.category_name,
            v.venue_name
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN category c ON e.category_id = c.category_id
        ORDER BY e.event_starting_date;
    """

    cursor.execute(query)
    events = cursor.fetchall()

    cursor.close()
    conn.close()

    return events


def get_event_by_id(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            e.event_id,
            e.event_name,
            e.event_starting_date,
            e.event_ending_date,
            e.event_total_price,
            e.booking_deadline,
            e.event_description,
            e.event_image,
            e.category_id,
            c.category_name,
            v.venue_name,
            v.suitability AS venue_suitability
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN category c ON e.category_id = c.category_id
        WHERE e.event_id = %s;
    """

    cursor.execute(query, (event_id,))
    event = cursor.fetchone()

    cursor.close()
    conn.close()

    return event

    
def get_event_conditions(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT c.condition_name
        FROM event_condition ec
        JOIN condition_tbl c ON ec.condition_id = c.condition_id
        WHERE ec.event_id = %s
        ORDER BY c.condition_name
    """

    cursor.execute(query, (event_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def check_login(username, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM users
        WHERE username = %s
    """

    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return user

    return None


def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    hashed_password = generate_password_hash(password)

    query = """
        INSERT INTO users (username, password_hash, role)
        VALUES (%s, %s, 'standard')
    """

    cursor.execute(query, (username, hashed_password))
    conn.commit()

    cursor.close()
    conn.close()


def user_already_booked(user_id, event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT booking_id
        FROM booking
        WHERE user_id = %s AND event_id = %s AND booking_status = 'confirmed'
    """

    cursor.execute(query, (user_id, event_id))
    booking = cursor.fetchone()

    cursor.close()
    conn.close()

    return booking is not None


def get_confirmed_booking_count(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT COUNT(*) AS total
        FROM booking
        WHERE event_id = %s AND booking_status = 'confirmed'
    """

    cursor.execute(query, (event_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result["total"]


def get_event_capacity(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT v.capacity
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        WHERE e.event_id = %s
    """

    cursor.execute(query, (event_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result["capacity"] if result else 0


def user_already_waiting(user_id, event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT wait_id
        FROM waiting_list
        WHERE user_id = %s AND event_id = %s AND wait_status = 'waiting'
    """

    cursor.execute(query, (user_id, event_id))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result is not None


def join_waiting_list(user_id, event_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO waiting_list (user_id, event_id, wait_status)
        VALUES (%s, %s, 'waiting')
    """

    cursor.execute(query, (user_id, event_id))
    conn.commit()

    cursor.close()
    conn.close()


def column_exists(table_name, column_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT COUNT(*) AS total
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s""",
        (table_name, column_name)
    )
    exists = cursor.fetchone()["total"] > 0
    cursor.close(); conn.close()
    return exists


def get_user_bookings(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    has_charge_amount = column_exists("booking", "cancellation_charge_amount")
    has_charge_percent = column_exists("booking", "cancellation_charge_percent")
    charge_amount_sql = "b.cancellation_charge_amount" if has_charge_amount else "0.00"
    charge_percent_sql = "b.cancellation_charge_percent" if has_charge_percent else "0"

    query = f"""
        SELECT 
            b.booking_id,
            b.booking_date,
            b.total_price,
            b.discount_amount,
            b.discount_type,
            b.booking_status,
            {charge_amount_sql} AS cancellation_charge_amount,
            {charge_percent_sql} AS cancellation_charge_percent,
            e.event_name,
            e.event_starting_date,
            e.event_ending_date,
            v.venue_name
        FROM booking b
        JOIN event e ON b.event_id = e.event_id
        JOIN venue v ON e.venue_id = v.venue_id
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """

    cursor.execute(query, (user_id,))
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    return bookings


def get_user_waiting_list(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            w.wait_id,
            w.joined_at,
            w.wait_status,
            e.event_name,
            e.event_starting_date,
            e.event_ending_date,
            v.venue_name
        FROM waiting_list w
        JOIN event e ON w.event_id = e.event_id
        JOIN venue v ON e.venue_id = v.venue_id
        WHERE w.user_id = %s
        ORDER BY w.joined_at DESC
    """

    cursor.execute(query, (user_id,))
    waiting_entries = cursor.fetchall()

    cursor.close()
    conn.close()

    return waiting_entries


def get_booking_for_user(booking_id, user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            b.booking_id,
            b.user_id,
            b.total_price,
            b.booking_status,
            e.event_id,
            e.event_name,
            e.event_starting_date
        FROM booking b
        JOIN event e ON b.event_id = e.event_id
        WHERE b.booking_id = %s AND b.user_id = %s
    """

    cursor.execute(query, (booking_id, user_id))
    booking = cursor.fetchone()

    cursor.close()
    conn.close()

    return booking


def calculate_cancellation_charge(total_price, event_starting_date):
    today = date.today()
    days_before_event = (event_starting_date - today).days

    if days_before_event >= 40:
        charge_percent = 0
    elif 25 <= days_before_event <= 39:
        charge_percent = 40
    else:
        charge_percent = 100

    charge_amount = round((float(total_price) * charge_percent) / 100, 2)

    return {
        "charge_percent": charge_percent,
        "charge_amount": charge_amount
    }


def update_booking_to_cancelled(booking_id, user_id, charge_amount=0, charge_percent=0):
    conn = get_connection()
    cursor = conn.cursor()

    # If migration_optional.sql has been applied, store the visible cancellation charge.
    # Fallback keeps the system working on older databases.
    try:
        query = """
            UPDATE booking
            SET booking_status = 'cancelled',
                cancellation_charge_amount = %s,
                cancellation_charge_percent = %s
            WHERE booking_id = %s AND user_id = %s AND booking_status = 'confirmed'
        """
        cursor.execute(query, (charge_amount, charge_percent, booking_id, user_id))
    except Exception:
        conn.rollback()
        query = """
            UPDATE booking
            SET booking_status = 'cancelled'
            WHERE booking_id = %s AND user_id = %s AND booking_status = 'confirmed'
        """
        cursor.execute(query, (booking_id, user_id))
    conn.commit()

    success = cursor.rowcount > 0

    cursor.close()
    conn.close()

    return success


def get_first_waiting_user(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT wait_id, user_id
        FROM waiting_list
        WHERE event_id = %s AND wait_status = 'waiting'
        ORDER BY joined_at ASC
        LIMIT 1
    """

    cursor.execute(query, (event_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result


def mark_waiting_as_promoted(wait_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE waiting_list
        SET wait_status = 'promoted'
        WHERE wait_id = %s
    """

    cursor.execute(query, (wait_id,))
    conn.commit()

    cursor.close()
    conn.close()


def create_promoted_booking(user_id, event_id, total_price):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO booking (
            user_id,
            event_id,
            total_price,
            discount_amount,
            discount_type,
            booking_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(query, (user_id, event_id, total_price, 0.00, "none", "confirmed"))
    conn.commit()

    cursor.close()
    conn.close()


def calculate_advance_discount_percent(event_starting_date):
    today = date.today()
    days_in_advance = (event_starting_date - today).days

    if 50 <= days_in_advance <= 60:
        return 20
    elif 35 <= days_in_advance < 50:
        return 15
    elif 25 <= days_in_advance < 35:
        return 10
    elif 15 <= days_in_advance < 25:
        return 5
    else:
        return 0


def calculate_best_discount(event_starting_date, total_price, is_student):
    advance_percent = calculate_advance_discount_percent(event_starting_date)
    student_percent = 10 if is_student else 0

    if student_percent > advance_percent:
        chosen_percent = student_percent
        discount_type = "student"
    elif advance_percent > 0:
        chosen_percent = advance_percent
        discount_type = f"advance_{advance_percent}%"
    else:
        chosen_percent = 0
        discount_type = "none"

    discount_amount = round((total_price * chosen_percent) / 100, 2)
    final_price = round(total_price - discount_amount, 2)

    return {
        "advance_percent": advance_percent,
        "student_percent": student_percent,
        "chosen_percent": chosen_percent,
        "discount_type": discount_type,
        "discount_amount": discount_amount,
        "final_price": final_price
    }


def create_booking_with_discount(user_id, event_id, total_price, discount_amount, discount_type):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO booking (
            user_id,
            event_id,
            total_price,
            discount_amount,
            discount_type,
            booking_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (user_id, event_id, total_price, discount_amount, discount_type, "confirmed")
    )
    conn.commit()
    booking_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return booking_id


def get_all_categories():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT category_id, category_name
        FROM category
        ORDER BY category_name ASC
    """

    cursor.execute(query)
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return categories


def get_all_conditions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT condition_id, condition_name
        FROM condition_tbl
        ORDER BY condition_name ASC
    """

    cursor.execute(query)
    conditions = cursor.fetchall()

    cursor.close()
    conn.close()

    return conditions


def get_all_events_admin():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            e.event_id,
            e.event_name,
            e.event_starting_date,
            e.event_ending_date,
            e.event_total_price,
            e.booking_deadline,
            e.event_description,
            e.event_image,
            e.category_id,
            v.venue_name,
            v.capacity,
            c.category_name
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN category c ON e.category_id = c.category_id
        ORDER BY e.event_starting_date ASC
    """

    cursor.execute(query)
    events = cursor.fetchall()

    cursor.close()
    conn.close()

    return events


def get_all_venues():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT venue_id, venue_name, address, capacity, venue_image, suitability
        FROM venue
        ORDER BY venue_name ASC
    """

    cursor.execute(query)
    venues = cursor.fetchall()

    cursor.close()
    conn.close()

    return venues


def admin_add_event(event_name, event_starting_date, event_ending_date,
                    event_total_price, venue_id, booking_deadline,
                    event_description, event_image, category_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO event (
            event_name,
            event_starting_date,
            event_ending_date,
            event_total_price,
            venue_id,
            booking_deadline,
            event_description,
            event_image,
            category_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(query, (
        event_name,
        event_starting_date,
        event_ending_date,
        event_total_price,
        venue_id,
        booking_deadline,
        event_description,
        event_image,
        category_id
    ))
    conn.commit()
    event_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return event_id


def add_event_conditions(event_id, condition_ids):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO event_condition (event_id, condition_id)
        VALUES (%s, %s)
    """

    for condition_id in condition_ids:
        cursor.execute(query, (event_id, condition_id))

    conn.commit()
    cursor.close()
    conn.close()


def get_event_full_by_id(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            event_id,
            event_name,
            event_starting_date,
            event_ending_date,
            event_total_price,
            venue_id,
            booking_deadline,
            event_description,
            event_image,
            category_id
        FROM event
        WHERE event_id = %s
    """

    cursor.execute(query, (event_id,))
    event = cursor.fetchone()

    cursor.close()
    conn.close()

    return event


def get_event_condition_ids(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT condition_id
        FROM event_condition
        WHERE event_id = %s
    """

    cursor.execute(query, (event_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [row[0] for row in rows]


def clear_event_conditions(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = "DELETE FROM event_condition WHERE event_id = %s"
    cursor.execute(query, (event_id,))
    conn.commit()

    cursor.close()
    conn.close()


def admin_update_event(event_id, event_name, event_starting_date, event_ending_date,
                       event_total_price, venue_id, booking_deadline,
                       event_description, event_image, category_id):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE event
        SET
            event_name = %s,
            event_starting_date = %s,
            event_ending_date = %s,
            event_total_price = %s,
            venue_id = %s,
            booking_deadline = %s,
            event_description = %s,
            event_image = %s,
            category_id = %s
        WHERE event_id = %s
    """

    cursor.execute(query, (
        event_name,
        event_starting_date,
        event_ending_date,
        event_total_price,
        venue_id,
        booking_deadline,
        event_description,
        event_image,
        category_id,
        event_id
    ))
    conn.commit()

    success = cursor.rowcount >= 0

    cursor.close()
    conn.close()

    return success


def admin_delete_event(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM event_condition WHERE event_id = %s", (event_id,))
    cursor.execute("DELETE FROM waiting_list WHERE event_id = %s", (event_id,))
    cursor.execute("DELETE FROM booking WHERE event_id = %s", (event_id,))
    cursor.execute("DELETE FROM event WHERE event_id = %s", (event_id,))
    conn.commit()

    success = cursor.rowcount > 0

    cursor.close()
    conn.close()

    return success


def get_report_bookings_per_event():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            e.event_name,
            COUNT(b.booking_id) AS total_bookings
        FROM event e
        LEFT JOIN booking b
            ON e.event_id = b.event_id
            AND b.booking_status = 'confirmed'
        GROUP BY e.event_id, e.event_name
        ORDER BY total_bookings DESC, e.event_name ASC
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_report_revenue_per_event():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            e.event_name,
            COALESCE(SUM(b.total_price), 0) AS total_revenue
        FROM event e
        LEFT JOIN booking b
            ON e.event_id = b.event_id
            AND b.booking_status = 'confirmed'
        GROUP BY e.event_id, e.event_name
        ORDER BY total_revenue DESC, e.event_name ASC
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_report_remaining_tickets():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            e.event_name,
            v.capacity,
            COUNT(b.booking_id) AS confirmed_bookings,
            (v.capacity - COUNT(b.booking_id)) AS remaining_tickets
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN booking b
            ON e.event_id = b.event_id
            AND b.booking_status = 'confirmed'
        GROUP BY e.event_id, e.event_name, v.capacity
        ORDER BY remaining_tickets ASC, e.event_name ASC
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows

def get_event_conditions_text(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT event_conditions
        FROM event
        WHERE event_id = %s
    """

    try:
        cursor.execute(query, (event_id,))
        row = cursor.fetchone()
    except Exception:
        row = None

    cursor.close()
    conn.close()

    if row and row.get("event_conditions"):
        return row["event_conditions"]
    return ""


def save_event_conditions_text(event_id, conditions_text):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE event
        SET event_conditions = %s
        WHERE event_id = %s
    """

    cursor.execute(query, (conditions_text, event_id))
    conn.commit()

    cursor.close()
    conn.close()


def get_filtered_events(search_term="", category_id="", free_only=False, month=""):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            e.event_id,
            e.event_name,
            e.event_starting_date,
            e.event_ending_date,
            e.event_total_price,
            e.event_description,
            e.event_image,
            e.category_id,
            c.category_name,
            v.venue_name
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN category c ON e.category_id = c.category_id
        WHERE 1=1
    """
    params = []

    if search_term:
        query += " AND (e.event_name LIKE %s OR e.event_description LIKE %s OR v.venue_name LIKE %s)"
        like = f"%{search_term}%"
        params.extend([like, like, like])

    if category_id:
        query += " AND e.category_id = %s"
        params.append(category_id)

    if free_only:
        query += " AND e.event_total_price = 0"

    if month:
        query += " AND DATE_FORMAT(e.event_starting_date, '%Y-%m') = %s"
        params.append(month)

    query += " ORDER BY e.event_starting_date ASC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def get_event_days(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT event_day_id, event_date, day_price
        FROM event_day
        WHERE event_id = %s
        ORDER BY event_date ASC
    """
    cursor.execute(query, (event_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def get_total_for_selected_days(day_ids):
    if not day_ids:
        return 0
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(day_ids))
    query = f"SELECT COALESCE(SUM(day_price),0) AS total FROM event_day WHERE event_day_id IN ({placeholders})"
    cursor.execute(query, tuple(day_ids))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return float(row['total']) if row else 0


def create_booking_with_discount_and_days(user_id, event_id, total_price, discount_amount, discount_type, selected_day_ids):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO booking (
            user_id,
            event_id,
            total_price,
            discount_amount,
            discount_type,
            booking_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, event_id, total_price, discount_amount, discount_type, 'confirmed'))
    booking_id = cursor.lastrowid
    if selected_day_ids:
        bd_query = "INSERT INTO booked_days (booking_id, event_day_id) VALUES (%s, %s)"
        for day_id in selected_day_ids:
            cursor.execute(bd_query, (booking_id, day_id))
    conn.commit()
    cursor.close(); conn.close()
    return booking_id


def delete_venue(venue_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE event SET venue_id = NULL WHERE venue_id = %s", (venue_id,))
    cursor.execute("DELETE FROM venue WHERE venue_id = %s", (venue_id,))
    conn.commit(); cursor.close(); conn.close()


def add_venue(venue_name, address, capacity):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO venue (venue_name, address, capacity) VALUES (%s,%s,%s)", (venue_name, address, capacity))
    conn.commit(); cursor.close(); conn.close()



def get_event_suitability(event_id):
    """Suitability belongs to venue, not event.
    Each venue has a capacity and is suitable for event types.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT v.suitability
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        WHERE e.event_id = %s
    """, (event_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["suitability"] if row and row.get("suitability") else ""


def get_report_full():
    """Comprehensive report data for the admin reports page."""
    conn = get_connection(); cursor = conn.cursor(dictionary=True)

    # Summary KPIs
    cursor.execute("SELECT COUNT(*) AS total_events FROM event")
    total_events = cursor.fetchone()['total_events']

    cursor.execute("SELECT COUNT(*) AS total_users FROM users WHERE role='standard'")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT COUNT(*) AS total_bookings FROM booking WHERE booking_status='confirmed'")
    total_bookings = cursor.fetchone()['total_bookings']

    cursor.execute("SELECT COALESCE(SUM(total_price),0) AS total_revenue FROM booking WHERE booking_status='confirmed'")
    total_revenue = float(cursor.fetchone()['total_revenue'])

    cursor.execute("SELECT COUNT(*) AS total_cancelled FROM booking WHERE booking_status='cancelled'")
    total_cancelled = cursor.fetchone()['total_cancelled']

    cursor.execute("SELECT COUNT(*) AS total_waiting FROM waiting_list WHERE wait_status='waiting'")
    total_waiting = cursor.fetchone()['total_waiting']

    # Per-event detailed stats
    cursor.execute("""
        SELECT
            e.event_id, e.event_name, e.event_starting_date, e.event_total_price,
            c.category_name, v.venue_name, v.capacity,
            COUNT(CASE WHEN b.booking_status='confirmed' THEN 1 END) AS confirmed_bookings,
            COUNT(CASE WHEN b.booking_status='cancelled' THEN 1 END) AS cancelled_bookings,
            COALESCE(SUM(CASE WHEN b.booking_status='confirmed' THEN b.total_price END),0) AS revenue,
            (v.capacity - COUNT(CASE WHEN b.booking_status='confirmed' THEN 1 END)) AS remaining_tickets
        FROM event e
        LEFT JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN category c ON e.category_id = c.category_id
        LEFT JOIN booking b ON e.event_id = b.event_id
        GROUP BY e.event_id, e.event_name, e.event_starting_date, e.event_total_price,
                 c.category_name, v.venue_name, v.capacity
        ORDER BY e.event_starting_date ASC
    """)
    events_stats = cursor.fetchall()
    for row in events_stats:
        row['revenue'] = float(row['revenue'])
        row['fill_rate'] = round((row['confirmed_bookings'] / row['capacity'] * 100), 1) if row['capacity'] else 0

    # Bookings by category
    cursor.execute("""
        SELECT c.category_name, COUNT(b.booking_id) AS bookings
        FROM booking b
        JOIN event e ON b.event_id = e.event_id
        LEFT JOIN category c ON e.category_id = c.category_id
        WHERE b.booking_status = 'confirmed'
        GROUP BY c.category_name ORDER BY bookings DESC
    """)
    category_stats = cursor.fetchall()

    # Revenue by category
    cursor.execute("""
        SELECT c.category_name, COALESCE(SUM(b.total_price),0) AS revenue
        FROM booking b
        JOIN event e ON b.event_id = e.event_id
        LEFT JOIN category c ON e.category_id = c.category_id
        WHERE b.booking_status = 'confirmed'
        GROUP BY c.category_name ORDER BY revenue DESC
    """)
    category_revenue = cursor.fetchall()
    for r in category_revenue:
        r['revenue'] = float(r['revenue'])

    # Monthly bookings trend
    cursor.execute("""
        SELECT DATE_FORMAT(booking_date, '%Y-%m') AS month, COUNT(*) AS bookings
        FROM booking WHERE booking_status='confirmed'
        GROUP BY month ORDER BY month ASC LIMIT 12
    """)
    monthly_bookings = cursor.fetchall()

    # Discount usage
    cursor.execute("""
        SELECT discount_type, COUNT(*) AS count, COALESCE(SUM(discount_amount),0) AS total_saved
        FROM booking WHERE booking_status='confirmed'
        GROUP BY discount_type ORDER BY count DESC
    """)
    discount_stats = cursor.fetchall()
    for r in discount_stats:
        r['total_saved'] = float(r['total_saved'])

    # Top events by revenue
    cursor.execute("""
        SELECT e.event_name, COALESCE(SUM(b.total_price),0) AS revenue
        FROM booking b JOIN event e ON b.event_id=e.event_id
        WHERE b.booking_status='confirmed'
        GROUP BY e.event_name ORDER BY revenue DESC LIMIT 5
    """)
    top_revenue = cursor.fetchall()
    for r in top_revenue:
        r['revenue'] = float(r['revenue'])

    # Waiting list by event
    cursor.execute("""
        SELECT e.event_name, COUNT(w.wait_id) AS waiting
        FROM waiting_list w JOIN event e ON w.event_id=e.event_id
        WHERE w.wait_status='waiting'
        GROUP BY e.event_name ORDER BY waiting DESC
    """)
    waiting_stats = cursor.fetchall()

    cursor.close(); conn.close()
    return {
        'total_events': total_events,
        'total_users': total_users,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_cancelled': total_cancelled,
        'total_waiting': total_waiting,
        'events_stats': events_stats,
        'category_stats': category_stats,
        'category_revenue': category_revenue,
        'monthly_bookings': monthly_bookings,
        'discount_stats': discount_stats,
        'top_revenue': top_revenue,
        'waiting_stats': waiting_stats,
    }



def add_venue_with_image(venue_name, address, capacity, venue_image=None, suitability=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO venue (venue_name, address, capacity, venue_image, suitability) VALUES (%s,%s,%s,%s,%s)",
        (venue_name, address, int(capacity), venue_image, suitability)
    )
    conn.commit(); cursor.close(); conn.close()


def update_venue(venue_id, venue_name, address, capacity, venue_image=None, suitability=None):
    conn = get_connection(); cursor = conn.cursor()
    if venue_image:
        cursor.execute(
            "UPDATE venue SET venue_name=%s, address=%s, capacity=%s, venue_image=%s, suitability=%s WHERE venue_id=%s",
            (venue_name, address, int(capacity), venue_image, suitability, venue_id)
        )
    else:
        cursor.execute(
            "UPDATE venue SET venue_name=%s, address=%s, capacity=%s, suitability=%s WHERE venue_id=%s",
            (venue_name, address, int(capacity), suitability, venue_id)
        )
    conn.commit(); cursor.close(); conn.close()


def get_venue_by_id(venue_id):
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT venue_id, venue_name, address, capacity, venue_image, suitability FROM venue WHERE venue_id=%s",
        (venue_id,)
    )
    row = cursor.fetchone(); cursor.close(); conn.close(); return row


def get_all_users_admin():
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, role FROM users ORDER BY username ASC")
    rows = cursor.fetchall(); cursor.close(); conn.close(); return rows


def admin_update_user_role(user_id, role):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
    conn.commit(); cursor.close(); conn.close()

def admin_delete_user(user_id):
    """Delete a user safely from the admin panel.
    Related waiting-list entries, booked day links and bookings are deleted first to satisfy foreign-key constraints.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return {"success": False, "message": "User not found."}

        # Avoid deleting the only admin account, because the system would become impossible to administer.
        if user["role"] == "admin":
            cursor.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'")
            if cursor.fetchone()["admin_count"] <= 1:
                return {"success": False, "message": "Cannot delete the only admin account."}

        cursor.execute("DELETE FROM waiting_list WHERE user_id = %s", (user_id,))
        cursor.execute("""
            DELETE bd FROM booked_days bd
            JOIN booking b ON bd.booking_id = b.booking_id
            WHERE b.user_id = %s
        """, (user_id,))
        cursor.execute("DELETE FROM booking WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"success": True, "message": f"User '{user['username']}' deleted successfully."}
    except Exception as exc:
        conn.rollback()
        return {"success": False, "message": f"Could not delete user: {exc}"}
    finally:
        cursor.close(); conn.close()


def update_user_password(user_id, new_password):
    conn = get_connection(); cursor = conn.cursor()
    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_password, user_id))
    conn.commit(); cursor.close(); conn.close()


def verify_user_password(user_id, password):
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone(); cursor.close(); conn.close()
    return bool(row and check_password_hash(row['password_hash'], password))

def can_reduce_event_price(event_id):
    """Return whether admin may apply the BCE 25% price reduction rule.
    Rule from the brief: within 10 days of an event, if less than 50% of tickets are booked, admin can lower ticket price by at least 25%.
    """
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.event_id, e.event_starting_date, e.event_total_price, v.capacity,
               COUNT(CASE WHEN b.booking_status='confirmed' THEN 1 END) AS confirmed_bookings
        FROM event e
        JOIN venue v ON e.venue_id = v.venue_id
        LEFT JOIN booking b ON e.event_id = b.event_id
        WHERE e.event_id = %s
        GROUP BY e.event_id, e.event_starting_date, e.event_total_price, v.capacity
    """, (event_id,))
    row = cursor.fetchone(); cursor.close(); conn.close()
    if not row:
        return {"allowed": False, "reason": "Event not found."}
    days_until = (row["event_starting_date"] - date.today()).days
    fill_rate = (row["confirmed_bookings"] / row["capacity"]) if row["capacity"] else 1
    if days_until < 0:
        return {"allowed": False, "reason": "Event has already started or passed."}
    if days_until > 10:
        return {"allowed": False, "reason": f"Not within 10 days yet ({days_until} days remaining)."}
    if fill_rate >= 0.5:
        return {"allowed": False, "reason": f"At least 50% booked already ({round(fill_rate*100,1)}%)."}
    return {"allowed": True, "reason": f"Eligible: only {round(fill_rate*100,1)}% booked with {days_until} day(s) remaining."}


def reduce_event_price_if_allowed(event_id):
    status = can_reduce_event_price(event_id)
    if not status["allowed"]:
        return {"success": False, "message": "Price was not reduced: " + status["reason"]}
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT event_total_price FROM event WHERE event_id = %s", (event_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); conn.close()
        return {"success": False, "message": "Event not found."}
    old_price = float(row["event_total_price"])
    new_price = round(old_price * 0.75, 2)
    cursor.execute("UPDATE event SET event_total_price = %s WHERE event_id = %s", (new_price, event_id))
    conn.commit(); cursor.close(); conn.close()
    return {"success": True, "message": f"Ticket price reduced by 25% from £{old_price:.2f} to £{new_price:.2f}."}
