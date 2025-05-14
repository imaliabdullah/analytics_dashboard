# Analytics Dashboard Backend

A Flask-based backend service for the Analytics Dashboard.

## Setup Instructions

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Update the values in `.env` with your configuration

4. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

5. Run the application:
```bash
flask run
```

## Project Structure

```
analytics_dashboard/
├── app/
│   ├── __init__.py
│   ├── app.py/
│   ├── models.py/
│   ├── routes.py/
│   ├── services.py/
├── migrations/
├── tests/
├── __init__.py
├── .coverage
├── .env
├── config.py
└── requirements.txt
├── run.py
├── setup.py
``` 