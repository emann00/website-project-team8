Web Security Project

* Team Members

Eman Ali : Developed the vulnerable version of the website and implemented the initial functionality and vulnerabilities.
Ahmed Saad : Worked on securing the application, fixing CSRF and OS Command Injection vulnerabilities.
Asser Ayman : Worked on securing the application, fixing XSS and Path Traversal vulnerabilities.
Hazem Ahmed : Worked on securing the application, fixing SSRF and SSTI vulnerabilities.
Ahmed Atef : Worked on securing the application, fixing SQL Injection and Open Redirect vulnerabilities.

# Idea

The idea of the project is to build a small e-commerce website that demonstrates common web security vulnerabilities.

The project has two versions:

* Vulnerable version: contains intentionally insecure code that allows the vulnerabilities to be demonstrated.
* Secure version: keeps the same basic functionality but applies security measures to prevent the vulnerabilities.

This allows us to see how each vulnerability works and how it can be fixed.

# How It Works

The website is built using Flask and SQLite. Users can log in, browse products, leave reviews, update their account information, and track orders.

The vulnerable version contains several security issues, including SQL Injection, XSS, CSRF, SSRF, SSTI, Command Injection, Path Traversal, and Open Redirect.

The secure version uses different security techniques such as input validation, safe output handling, parameterized SQL queries, CSRF protection, and safer file and URL handling.

There is also a small internal "supplier service" used to demonstrate the SSRF vulnerability. The main website communicates with this service locally.

Both versions can be run locally using the provided "start.sh" script.

# Requirements

* Python 3
* Flask
* Flask-WTF (used for CSRF protection in the secure version)
* SQLite
* A web browser

Python dependencies are listed in each version's `requirements.txt` file.

# Running the Project

For the vulnerable version:

```bash
cd vulnerable-website
./start.sh
```

For the secure version:

```bash
cd secure-website
./start.sh
```

The vulnerable website runs locally on:

```text
http://127.0.0.1:5000
```

The secured website runs on:

```text
http://127.0.0.1:5002
```
