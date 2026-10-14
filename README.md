# Bristol Community Events

**Event booking and management web application** built with Python, Flask and MySQL.

A full-stack project bringing event discovery, ticket reservations and administrative management into a single web application, with separate attendee and administrator workflows.

## Tech stack

**Backend:** Python, Flask, MySQL, Jinja2  
**Frontend:** HTML, CSS, JavaScript  
**Other:** MySQL Connector/Python, Werkzeug, ReportLab

## Features

**Event discovery and booking**
- Explore events and venues, with event details and category-based filtering.
- Create an account, sign in, change passwords and manage bookings.
- Reserve tickets with venue-capacity checks and pricing rules.
- Support advance-booking and student discounts, plus multi-day event bookings.
- Join a waiting list when an event is fully booked.
- View booking history, cancel reservations and download PDF receipts.
- Follow a simulated payment workflow (no real transactions).

**Administration**
- Add, update and remove events and venues.
- Manage user accounts and view event, booking and revenue reports.
- Apply conditional ticket-price reductions.

## How it works

Flask handles routes, sessions and form processing. The database layer in `dbfunc.py` manages MySQL operations and booking logic. Jinja2 renders database-driven views; JavaScript and CSS support the interactive, responsive interface. ReportLab generates downloadable booking receipts.

## Project structure

```text
app.py               Flask routes and request handling
dbfunc.py            Database access and booking operations
templates/           Jinja2 page templates
static/css/          Stylesheets
static/img/          Site and event images
requirements.txt     Python dependencies
.env.example         Local configuration template
```

## Running locally

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set a new `SECRET_KEY` and your local MySQL connection details. Generate a suitable secret with:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Configure a local MySQL database with the tables expected by the application.
4. Start the app:

   ```bash
   python app.py
   ```
5. Open `http://127.0.0.1:5010`.

**Database availability:** The source archive did not include the database schema or seed data, so setup requires restoring a compatible MySQL database. The repository is provided as a code portfolio, not a hosted demonstration.

## Notes

This is a learning project rather than a production payment platform. Payments are simulated, and deployment would require additional security review and testing.
