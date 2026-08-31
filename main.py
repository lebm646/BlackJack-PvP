"""WSGI entry point used by Vercel and production WSGI servers."""

from src.app import app

if __name__ == '__main__':
    app.run(debug=True)
