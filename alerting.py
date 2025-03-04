import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def emailAlert(to_emails, subject, body):
    """
    Sends an email to multiple recipients.
    Args:
        to_emails (list): A list of email addresses to send the email to.
        subject (str): The subject of the email.
        body (str): The body content of the email.
    """
    smtp_server = 'smtp.gmail.com'
    port = 587
    from_email = 'ncgalertsystem@gmail.com'
    app_password = 'xpsk cedv cive qsgb'  
    
    if not isinstance(to_emails, list):
      to_emails = [to_emails]

    # Set up the MIMEMultipart object
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(from_email, app_password)  # Log in to your email account

            for to_email in to_emails:
                msg['To'] = to_email # update the current email in the loop
                server.sendmail(from_email, to_email, msg.as_string())  # Send the email

        print("Email sent successfully to all recipients!")

    except Exception as e:
        print(f"Error: {e}")



def format_and_send_alert_email(highCPUList, highMemList, highDiskList, datetime):
    """
    Formats the email body based on the provided server lists and sends the alert.

    Args:
        to_emails (list): A list of email addresses to send the email to.
        highCPUList (list): List of servers with high CPU usage.
        highMemList (list): List of servers with high memory usage.
        highDiskList (list): List of servers with high disk usage.
    """
    
    def format_list_section(server_list, resource_type):
        """Helper function to format a list of servers into a string."""
        if not server_list:
            return f"No servers are currently experiencing high {resource_type} usage."
        else:
            section_body = f"The following servers are currently experiencing high {resource_type} usage:\n"
            for server in server_list:
                section_body += f"- {server}\n"
            return section_body
    
    # Format the email body
    cpu_section = format_list_section(highCPUList, "CPU")
    mem_section = format_list_section(highMemList, "Memory")
    disk_section = format_list_section(highDiskList, "Disk")
    
    body = f"""
    Dear Operations Team,
    This is an automated alert from regarding high resource utilization detected on several infrastructure servers. Immediate attention may be required to prevent performance issues or service disruptions.

    **High CPU Usage:**
    {cpu_section}

    **High Memory Usage:**
    {mem_section}

    **High Disk Usage:**
    {disk_section}

    **Action Required:**

    *   Please investigate the servers listed above as soon as possible.
    *   Analyze the root cause of the high resource usage (e.g., resource leaks, background processes, etc.)
    *   Take appropriate action to resolve the issue and restore normal resource utilization levels.
    * If possible adjust the threshold to avoid continuous alerts.

    **Additional Information:**

    *   This alert was generated at: {datetime}
    *   The data was gathered from the last available logs.
    *   For further details, please refer to the Infrastructure Monitoring Dashboard or contact the monitoring team.

    Thank you,

    The Infrastructure Monitoring System
    """
    
    subject = f"ALERT: High CPU/Memory/Disk Usage on {len(highCPUList) + len(highMemList) + len(highDiskList)} Servers"
    
    return subject, body




# val = [i for i in range(10) if i % 2 == 0]
# smtp_server = 'smtp.gmail.com'
# port = 587
# from_email = 'ncgalertsystem@gmail.com'
# to_email = 'mellowfingers.skz@gmail.com'
# app_password = 'xpsk cedv cive qsgb'
# subject = 'This is the subject of the mail'
# body = f"""Hi... I began writing the body from here
# I want to see what it looks like and how I can have it done
# Trying out other values too like: {val}
# Okay bye

# Thanks
# Kind Regards"""

# # Set up the MIMEMultipart object
# msg = MIMEMultipart()
# msg['From'] = from_email
# msg['To'] = to_email
# msg['Subject'] = subject

# # Attach the email body
# msg.attach(MIMEText(body, 'plain'))


# # Send the email
# try:
#     # Create a secure SSL context
#     with smtplib.SMTP(smtp_server, port) as server:
#         server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
#         server.login(from_email, app_password)  # Log in to your email account
#         server.sendmail(from_email, to_email, msg.as_string())  # Send the email
#     print("Email sent successfully!")
# except Exception as e:
#     print(f"Error: {e}")




# Constants (consider moving these to a config file for better management

