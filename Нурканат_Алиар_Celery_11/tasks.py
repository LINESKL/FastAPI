from celery import shared_task
import time

@shared_task
def send_email_task(recipient: str, subject: str, body: str):
    print(f"Starting email task for {recipient}")
    time.sleep(5)  
    print(f"Email sent to {recipient} with subject '{subject}' and body '{body}'")
    return {"status": "success", "recipient": recipient, "subject": subject}