from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.jobs.send_quote_email")
def send_quote_email(quote_id: str, email: str) -> None:
    print(f"[email:log] Quote {quote_id} confirmation queued for {email}")


@celery_app.task(name="app.tasks.jobs.send_contact_email")
def send_contact_email(contact_id: str, email: str) -> None:
    print(f"[email:log] Contact request {contact_id} confirmation queued for {email}")


@celery_app.task(name="app.tasks.jobs.refresh_dashboard_metrics")
def refresh_dashboard_metrics() -> None:
    print("[metrics:log] Dashboard metrics refresh requested")

