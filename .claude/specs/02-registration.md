---
# Spec: Registration

## Overview
The registration feature allows new users to create an account by providing a username, email, and password. The password is hashed and stored securely. Upon successful registration, the user is redirected to the login page. This feature implements step 2 of the Spendly roadmap, following the landing page redesign.

## Depends on
Step 1: Landing page redesign

## Routes
No new routes (registration already implemented at GET /register and POST /register)

## Database changes
No database changes (users table already exists with required schema)

## Templates
- **Create:** None
- **Modify:** templates/register.html - Change form field from 'name' to 'username', update label and placeholder to reflect username input (e.g., "Choose a username")

## Files to change
- templates/register.html

## Files to create
- None

## New dependencies
No new dependencies (application already uses Werkzeug for password hashing)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend base.html

## Definition of done
- [ ] User can navigate to /register and see the registration form
- [ ] Form validation works: all fields are required and show appropriate errors when missing
- [ ] Upon submitting valid registration data, a new user is created in the database
- [ ] Password is properly hashed using werkzeug before storage
- [ ] Duplicate username or email prevents registration and shows appropriate error message
- [ ] After successful registration, user is redirected to the login page with a success message
- [ ] Registration form uses username field (not full name) matching the backend expectation
- [ ] All CSS in associated templates uses CSS variables, no hardcoded color values
---