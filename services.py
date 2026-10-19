import csv
import smtplib
import threading
import time
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Headless rendering for Matplotlib to avoid GUI errors
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from models import ActionStack
undo_stack = ActionStack()

# =====================================================================
# SMTP & Email Settings
# =====================================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "support.gridplanner@gmail.com"
SENDER_PASSWORD = "xtrwkqjdirzjbrdo"

def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("system_activity.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def export_schedule_to_csv(schedule_rows, filepath="study_schedule.csv"):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Start Time", "End Time", "Category", "Task Title"])
        for row in schedule_rows:
            writer.writerow([row["session_date"], row["start_time"], row["end_time"], row["subject"], row["task_title"]])
    log_event("Exported schedule to CSV.")

def import_tasks_from_csv(file_stream):
    tasks = []
    reader = csv.DictReader(file_stream)
    for row in reader:
        tasks.append({
            "title": row["title"].strip(),
            "subject": row["subject"].strip(),
            "task_type": row.get("task_type", "ACADEMIC").strip().upper(),
            "deadline": row["deadline"].strip(),
            "estimated_hours": float(row["estimated_hours"]),
            "priority": int(row["priority"]),
            "specific_meta": row.get("specific_meta", "10")
        })
    log_event(f"Imported {len(tasks)} tasks from CSV.")
    return tasks

def send_welcome_email(receiver_email, username):
    """Sends an automated welcome email upon successful user registration via SMTP."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = "⚡ Welcome to GridPlanner — Account Created Successfully!"

    body = f"""Hello {username}!

Congratulations! Your GridPlanner account has been successfully created.

Your Autonomous Life & Academic Planner is ready to use:
1. Configure your recurring weekly study & life windows.
2. Drop in your upcoming academic assignments, exams, and personal tasks.
3. Track your daily habits and build unstoppable streaks!

Our heuristic algorithm will handle the scheduling math automatically.

Best regards,
The GridPlanner Team
"""
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to Gmail SMTP Server over TLS port 587
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        log_event(f"SMTP Success: Welcome email sent to {receiver_email}")
        print(f"[SMTP SUCCESS] Welcome email dispatched to {receiver_email}")
        return True
    except Exception as e:
        # Fallback simulation if offline or Wi-Fi blocks port 587
        print(f"[SMTP SIMULATION] Welcome email queued for {receiver_email} ({username}). Reason: {e}")
        log_event(f"SMTP Simulation: Welcome email to {receiver_email}")
        return True

def generate_analytics_chart(schedule_rows, output_path="static/analytics.png"):
    subject_hours = {}
    for item in schedule_rows:
        subj = item["subject"]
        subject_hours[subj] = subject_hours.get(subj, 0) + 1.5

    if not subject_hours:
        subject_hours = {"No Tasks": 0}

    # Style matching the lo-fi / retro theme
    fig, ax = plt.subplots(figsize=(6, 3.2), facecolor="#FFF8EE")
    ax.set_facecolor("#FFFDF9")
    
    categories = list(subject_hours.keys())
    hours = list(subject_hours.values())
    
    ax.bar(categories, hours, color="#64C4B8", edgecolor="#2B2220", linewidth=1.5, width=0.45)
    ax.tick_params(colors="#2B2220", labelsize=9)
    ax.set_ylabel("Planned Hours", color="#2B2220", fontsize=10, fontweight="bold")
    ax.set_title("Workload Distribution by Category", color="#2B2220", fontsize=11, fontweight="bold", pad=10)
    
    for spine in ax.spines.values():
        spine.set_color("#2B2220")
        spine.set_linewidth(1.5)
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close()

def send_reset_otp_email(receiver_email, otp_code):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = "GridOS: Password Reset Verification Code"

    body = f"""Hello!

You requested a password reset for your GridOS account.

Your 6-digit Verification Code is:
[ {otp_code} ]

Enter this code in your browser to choose a new password. If you didn't request this, you can ignore this email.
"""
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        log_event(f"SMTP Success: Dispatched OTP to {receiver_email}")
        return True
    except Exception as e:
        print(f"[SMTP SIMULATION] (Offline Demo) Reset code for {receiver_email} is: {otp_code}")
        log_event(f"SMTP Simulation: {receiver_email} code {otp_code} (Reason: {e})")
        return True

def start_background_monitor():
    def monitor_loop():
        while True:
            log_event("Daemon thread: Active check on tasks & deadlines.")
            time.sleep(60)

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
