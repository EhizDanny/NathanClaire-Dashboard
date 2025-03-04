import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import datetime
import time
import sqlite3
import os

class AlertManager:
    def __init__(self, config_file='config.json', db_file='EdgeDB 2'):
        """
        Initializes the AlertManager with configuration and database.
        """
        self.config = self.load_config(config_file)
        self.smtp_server = self.config['smtp_server']
        self.port = self.config['port']
        self.from_email = self.config['from_email']
        self.app_password = self.config['app_password']
        self.thresholds = self.config['thresholds']
        self.db_file = db_file
        self.setup_database()
        self.alert_suppression = {}  # Dictionary to track suppressed alerts: {server: last_alert_time}

    def load_config(self, config_file):
        """Loads configuration from a JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file '{config_file}' not found.")
            # Set default config or raise the error if needed
            raise
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in '{config_file}'.")
            raise

    def setup_database(self):
        """Sets up the SQLite database for logging alerts."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                server TEXT,
                resource TEXT,
                level TEXT,
                value REAL,
                message TEXT,
            )
        """)
        conn.commit()
        conn.close()

    def send_email(self, to_emails, subject, body):
        """Sends an HTML email to multiple recipients."""
        if not isinstance(to_emails, list):
            to_emails = [to_emails]

        msg = MIMEMultipart('alternative')
        msg['From'] = self.from_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.from_email, self.app_password)

                for to_email in to_emails:
                    msg['To'] = to_email
                    server.sendmail(self.from_email, to_email, msg.as_string())

            print(f"Email sent successfully to {to_emails}!")
        except Exception as e:
            print(f"Error sending email: {e}")

    def log_alert(self, timestamp, server, resource, level, value, message):
        """Logs an alert to the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (timestamp, server, resource, level, value, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, server, resource, level, value, message))
        conn.commit()
        conn.close()

    # def should_send_alert(self, server, level, alert_suppression_time):
    #     """Checks if an alert should be sent based on suppression time."""
    #     now = time.time()
    #     last_alert_time = self.alert_suppression.get(server, {}).get(level, 0)

    #     if now - last_alert_time > alert_suppression_time:
    #         return True
    #     else:
    #         return False

    # def update_alert_suppression(self, server, level):
    #     """Updates the alert suppression time for a server and level."""
    #     now = time.time()
    #     if server not in self.alert_suppression:
    #         self.alert_suppression[server] = {}
    #     self.alert_suppression[server][level] = now

    def check_resource_usage(self, server, cpu_usage, mem_usage, disk_usage, current_datetime, recipients, ):
        """
        Checks CPU, memory, and disk usage against thresholds and sends alerts.
        """
        alerts_to_send = []

        # Resource checks
        resource_checks = {
            'CPU': (cpu_usage, 'cpu_thresholds', 'CPU Usage'),
            'Memory': (mem_usage, 'mem_thresholds', 'Memory Usage'),
            'Disk': (disk_usage, 'disk_thresholds', 'Disk Usage')
        }

        #  Loop through each resource ('CPU', 'Memory', 'Disk') and extracts:
        # resource: The name of the resource (e.g., "CPU").
        # usage: The current usage value (e.g., 85%).
        # thresholds_key: The key to look up the thresholds in the config (e.g., "cpu_thresholds").
        # title: the name to display in the email.
        for resource, (usage, thresholds_key, title) in resource_checks.items():
            thresholds = self.thresholds[thresholds_key]
            level = None
            message = ""

            if usage >= thresholds['critical']:
                level = 'critical'
                message = f"{title} is critically high at {usage:.2f}%."
            elif usage >= thresholds['warning']:
                level = 'warning'
                message = f"{title} is high at {usage:.2f}%."

            if level:
                # if self.should_send_alert(server, level, self.config['alert_suppression_time']):
                alerts_to_send.append((level, resource, usage, message))
                # self.update_alert_suppression(server, level)
                self.log_alert(current_datetime, server, resource, level, usage, message)

        if alerts_to_send:
            self.generate_and_send_alert_email(server, alerts_to_send, current_datetime, recipients)

    def generate_and_send_alert_email(self, server, alerts, current_datetime, recipients):
        """Generates and sends the email alert."""

        def format_list_section(alert_list):
            """Helper function to format a list of alerts into a string."""
            section_body = f"<ul>"
            for level, resource, usage, message in alert_list:
                section_body += f"<li><span style='color:{self.get_level_color(level)}'>{level.upper()}:</span> {resource} at {usage:.2f}% - {message}</li>"
            section_body += "</ul>"
            return section_body

        alert_section = format_list_section(alerts)

        # Customize the subject based on alert levels
        if any(level == "critical" for level, _, _, _ in alerts):
          subject = f"CRITICAL Alert: High Resource Usage Detected on Server {server}"
        elif any(level == "warning" for level, _, _, _ in alerts):
          subject = f"WARNING Alert: High Resource Usage Detected on Server {server}"
        else:
          subject = f"INFO Alert: High Resource Usage Detected on Server {server}"

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Infrastructure Alert</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }}
                h2 {{
                    color: #d9534f; /* Reddish color for headers */
                    margin-top: 0;
                    margin-bottom: 10px;
                }}
                p {{
                    margin-bottom: 10px;
                }}
                ul {{
                    list-style-type: disc;
                    margin-left: 20px;
                }}
                li {{
                    margin-bottom: 5px;
                }}
                .action-required {{
                    margin-top: 20px;
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 5px;
                }}
                .info {{
                    margin-top: 20px;
                    font-size: 0.9em;
                    color: #777;
                    border-top: 1px solid #ddd;
                    padding-top: 10px;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 0.9em;
                    color: #777;
                    border-top: 1px solid #ddd;
                    padding-top: 10px;
                    text-align: center
                }}
                .highlight{{
                    color: #d9534f;
                }}
                .critical {{
                    color: #F93827; /* Red */
                }}
                .warning {{
                    color: #FFA500; /* Orange */
                }}
                .info {{
                    color: #0000FF; /* Blue */
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <p>Dear <span class='highlight'>Operations Team</span>,</p>
                <p>This is an <strong>automated alert</strong> regarding high resource utilization detected on server {server}.</p>

                <h2>Alerts:</h2>
                {alert_section}

                <div class="action-required">
                    <h2>Action Required:</h2>
                    <ul>
                        <li>Please investigate the server listed above as soon as possible.</li>
                        <li>Analyze the root cause of the high resource usage (e.g., resource leaks, background processes, etc.)</li>
                        <li>Take appropriate action to resolve the issue and restore normal resource utilization levels.</li>
                        <li>If possible, adjust the threshold to avoid continuous alerts.</li>
                    </ul>
                </div>

                <div class="info">
                    <p><strong>Additional Information:</strong></p>
                    <ul>
                        <li>This alert was generated at: {current_datetime}</li>
                        <li>For further details, please refer to the Infrastructure Monitoring Dashboard or contact the monitoring team.</li>
                    </ul>
                </div>
                <div class='footer'>
                    <p>Thank you,</p>
                    <p>The Infrastructure Monitoring System</p>
                </div>
            </div>
        </body>
        </html>
        """

        self.send_email(recipients, subject, body)

    def get_level_color(self, level):
        """Returns the color code for a given alert level."""
        if level == "critical":
            return "#F93827"  # Red
        elif level == "warning":
            return "#FFA500"  # Orange
        # elif level == "info":
        #     return "#0000FF"  # Blue
        # else:
        #     return "#000000"  # Default to black


# Example usage (you can move this to your infraDash.py or another script)
if __name__ == "__main__":
    # Example configuration (you should load this from config.json)
    config = {
        "smtp_server": "smtp.gmail.com",
        "port": 587,
        "from_email": "ncgalertsystem@gmail.com",
        "app_password": "xpsk cedv cive qsgb",
        "thresholds": {
            "cpu_thresholds": {"info": 60, "warning": 80, "critical": 90},
            "mem_thresholds": {"info": 70, "warning": 85, "critical": 95},
            "disk_thresholds": {"info": 75, "warning": 85, "critical": 95},
        },
        "alert_suppression_time": 300, # Suppress alerts for the same server and level for 5 minutes (300 seconds)
    }
    
    # Create a config.json file if it does not exist
    if not os.path.exists("config.json"):
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

    alert_manager = AlertManager()

    recipients = ['mellowfingers.skz@gmail.com']

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Simulate some usage data (replace with your actual data)
    alert_manager.check_resource_usage("server1", 92, 88, 98, current_datetime, recipients)
    alert_manager.check_resource_usage("server2", 82, 91, 70, current_datetime, recipients)
    alert_manager.check_resource_usage("server3", 55, 65, 58, current_datetime, recipients)
    alert_manager.check_resource_usage("server1", 98, 90, 95, current_datetime, recipients)
    time.sleep(3)
    alert_manager.check_resource_usage("server1", 90, 89, 96, current_datetime, recipients)

