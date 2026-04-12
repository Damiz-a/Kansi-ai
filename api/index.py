"""Vercel Serverless entrypoint for Flask app."""

from app import app

# Expose the WSGI app for @vercel/python runtime.
handler = app
