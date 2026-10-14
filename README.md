# Bristol Community Events — Event Booking & Management System

A database-driven web application for exploring and booking events around Bristol, with dedicated customer and administrator interfaces. Developed for the **Web Development and Databases** module at **UWE Bristol** (2025–26), based on the *Bristol Events Management System* case study.

**Tech stack:** Python · Flask · MySQL · HTML · CSS · JavaScript · Jinja2 · ReportLab

## Overview

Bristol Community Events (BCE) brings event discovery, bookings and event administration into one application. Visitors can explore events and venues; signed-in users can make bookings and manage their records. Administrators have separate views for events, venues, users and reporting.

## Features

### Attendees
- Browse upcoming events, event details and categories, with filtering.
- Register, sign in and out, and change passwords.
- Make event bookings and go through a **simulated** payment flow (no real payment gateway).
- View and download PDF booking receipts with pricing information.
- View bookings in a personal wallet and cancel bookings.
- Join a waiting list for fully booked events.
- Handle discounted bookings, including advance-booking and student discounts.
- Select individual days for supported multi-day events.

### Administrators
- Manage events and venues, including venue suitability and capacity.
- Manage users and user roles.
- View booking, revenue and availability reports.
- Apply conditional event price reductions.

## Project structure

```text
app.py                Flask routes and application logic
dbfunc.py             MySQL queries and booking/database operations
templates/            Jinja2 page templates
static/css/           Stylesheets and responsive layout
static/img/           Event, venue and site imagery
requirements.txt      Python dependencies
.env.example          Example environment configuration (no secrets)
```

## Local setup

**Requirements:** Python 3.11+ and a running MySQL server with a database matching the application's schema.

1. Clone the repository and enter its directory.
2. Create and activate a Python virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and provide your own `SECRET_KEY` and MySQL credentials. Generate a session secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
5. Prepare a local MySQL database using your own compatible schema/data and set `DB_NAME` in `.env`.
6. Start the server with `python app.py` and open `http://127.0.0.1:5010`.

> **Database note:** The original ZIP did not contain a MySQL schema/dump. The project therefore cannot be run from a fresh clone until its database schema and any necessary sample records are restored. No database credentials or user records are distributed.

## Architecture and implementation

The Flask application (`app.py`) handles routing, sessions, form input and page rendering. SQL and business-logic helpers live in `dbfunc.py`, using MySQL Connector/Python. Jinja2 templates generate HTML from database data, while CSS and browser-side JavaScript provide the presentation and interactions. ReportLab generates PDF receipts. Passwords are checked against hashes using Werkzeug's password-hashing utilities.

The coursework brief required a responsive interface, relational database design, authenticated users, event capacity constraints, booking logic, discounts and administrative reporting. This repository represents the submitted implementation; it is a **coursework project**, not a production-ready ticketing service.

## Security and configuration

- Runtime settings and credentials are loaded from a local `.env` file, which is excluded from Git.
- A random Flask session secret must be supplied in `SECRET_KEY`.
- Password hashes are used rather than saving plaintext user passwords.
- Database queries use parameterised arguments in the project.
- `FLASK_DEBUG` defaults to `false`.
- The payment page is for demonstration, **not** live payment processing.

**Important:** Security has not been independently audited; do not deploy this coursework website publicly without reviewing permissions, CSRF protection, validation, upload handling and deployment configuration.

## Academic context

Created by **Insaf Fala**, as part of UWE Bristol's first-year *Web Development and Databases* module. The case study, assessment constraints and expected features were supplied in the 2025–26 module assessment brief.
