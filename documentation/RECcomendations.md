# Reccomendations API (Mobile)

## Status

This backend contains a recommendation module in `routes/reccomendation.py`, but **it is not registered** in `routes/__init__.py`.

Therefore, this module is currently **not reachable** from the Flask app.

---

If you later register it (e.g. `app.register_blueprint(reccomendations_bp, url_prefix='/...')`), document routes here.
