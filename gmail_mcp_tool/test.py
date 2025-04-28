from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pathlib import Path
import sys
import logging
import argparse
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('gmail_api_test')

# Define the scopes your app needs
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send'
]

def authenticate():
    """Authenticate with Gmail API."""
    logger.debug("Starting authentication process")
    creds = None
    # Define file paths using pathlib
    token_path = Path('gmail_mcp_tool/token.json')
    credentials_path = Path('gmail_mcp_tool/credentials.json')
    
    # Check if token file exists
    if token_path.exists():
        logger.debug("Found existing token file")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except ValueError as e:
            logger.error(f"Error loading credentials: {e}")
            # If we have an error with the token file, force re-authentication
            token_path.unlink(missing_ok=True)
            creds = None
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        logger.info("No valid credentials found, initiating OAuth flow")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES)
        # Adding access_type='offline' to get a refresh token
        creds = flow.run_local_server(
            port=8080,
            access_type='offline',
            prompt='consent'  # Force prompt to ensure refresh token is provided
        )
        logger.info("Successfully authenticated")
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        logger.debug("Saved credentials to token file")
    
    return creds

def create_message(sender, to, subject, message_text, html_content=None):
    """Create a message for an email.
    
    Args:
        sender: Email sender
        to: Email recipient(s)
        subject: Email subject
        message_text: Email body as plain text
        html_content: Email body as HTML (optional)
        
    Returns:
        An object containing a base64url encoded email message
    """
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Add plain text part
    text_part = MIMEText(message_text, 'plain')
    message.attach(text_part)
    
    # Add HTML part if provided
    if html_content:
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

    # Encode and convert to dict for the Gmail API
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': encoded_message}

def send_message(service, user_id, message):
    """Send an email message.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        message: Message to be sent (in the format returned by create_message).
        
    Returns:
        Dictionary containing the sent message details.
    """
    try:
        logger.debug(f"Sending message for user {user_id}")
        sent_message = service.users().messages().send(userId=user_id, body=message).execute()
        logger.info(f"Message sent successfully. Message ID: {sent_message['id']}")
        return sent_message
    except HttpError as error:
        logger.error(f"Error sending message: {error}", exc_info=True)
        return None

def modify_message(service, user_id, message_id, add_labels=None, remove_labels=None):
    """Modify the labels of a message.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        message_id: ID of the message to modify.
        add_labels: List of label IDs to add.
        remove_labels: List of label IDs to remove.
        
    Returns:
        Dictionary containing the modified message.
    """
    try:
        logger.debug(f"Modifying message {message_id} for user {user_id}")
        
        # Create the label modification request
        body = {}
        if add_labels:
            body['addLabelIds'] = add_labels
        if remove_labels:
            body['removeLabelIds'] = remove_labels
            
        # Execute the API call
        modified_message = service.users().messages().modify(
            userId=user_id, 
            id=message_id, 
            body=body
        ).execute()
        
        logger.info(f"Message {message_id} modified successfully.")
        return modified_message
    except HttpError as error:
        logger.error(f"Error modifying message: {error}", exc_info=True)
        return None

def list_messages(service, user_id='me', query='', max_results=10):
    """List messages in the user's mailbox.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        query: Search query (same format as Gmail search box).
        max_results: Maximum number of messages to return.
        
    Returns:
        List of messages.
    """
    try:
        logger.debug(f"Listing messages for user {user_id} with query: {query}")
        
        # Get message list
        response = service.users().messages().list(
            userId=user_id,
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = response.get('messages', [])
        logger.info(f"Found {len(messages)} messages matching query")
        
        return messages
    except HttpError as error:
        logger.error(f"Error listing messages: {error}", exc_info=True)
        return []

def get_message(service, user_id, message_id, format='full'):
    """Get a specific message.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        message_id: ID of the message to retrieve.
        format: Format of the message (full, minimal, raw).
        
    Returns:
        The specified message.
    """
    try:
        logger.debug(f"Getting message {message_id} for user {user_id}")
        message = service.users().messages().get(
            userId=user_id,
            id=message_id,
            format=format
        ).execute()
        
        logger.info(f"Successfully retrieved message {message_id}")
        return message
    except HttpError as error:
        logger.error(f"Error getting message: {error}", exc_info=True)
        return None

def test_gmail_send():
    """Test sending an email via the Gmail API."""
    logger.info("=== Testing Gmail Send Message API ===")
    
    # Authenticate and build service
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user's email address for the 'from' field
    profile = service.users().getProfile(userId='me').execute()
    sender_email = profile['emailAddress']
    
    # Get recipient email from user input
    recipient = input("Enter recipient email address: ")
    subject = "Test email from Gmail API"
    message_text = "This is a test email sent using the Gmail API."
    html_content = "<h1>Test Email</h1><p>This is a <b>test email</b> sent using the Gmail API.</p>"
    
    # Create the message
    message = create_message(sender_email, recipient, subject, message_text, html_content)
    
    # Send the message
    result = send_message(service, 'me', message)
    
    if result:
        logger.info(f"Test email sent successfully to {recipient}! Message ID: {result['id']}")
    else:
        logger.error("Failed to send test email.")

def test_gmail_modify():
    """Test modifying email labels via the Gmail API."""
    logger.info("=== Testing Gmail Modify Message API ===")
    
    # Authenticate and build service
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    
    # List recent emails to choose from
    print("Fetching recent messages...")
    messages = list_messages(service, max_results=5)
    
    if not messages:
        logger.error("No messages found to modify!")
        return
    
    # Display the messages for selection
    print("\nRecent messages:")
    for i, msg in enumerate(messages):
        message = get_message(service, 'me', msg['id'], format='metadata')
        subject = "No subject"
        for header in message['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
                break
        print(f"{i+1}. {subject[:50]}... (ID: {msg['id']})")
    
    # Get user selection
    try:
        selection = int(input("\nSelect a message to modify (number): ")) - 1
        if selection < 0 or selection >= len(messages):
            logger.error("Invalid selection")
            return
    except ValueError:
        logger.error("Invalid input")
        return
    
    message_id = messages[selection]['id']
    
    # Get current labels
    message = get_message(service, 'me', message_id)
    current_labels = message.get('labelIds', [])
    print(f"\nCurrent labels: {', '.join(current_labels) if current_labels else 'None'}")
    
    # Options for modification
    print("\nLabel options:")
    print("1. Add IMPORTANT label")
    print("2. Remove IMPORTANT label")
    print("3. Mark as read (remove UNREAD label)")
    print("4. Mark as unread (add UNREAD label)")
    
    choice = input("\nSelect an action (1-4): ")
    
    if choice == '1':
        result = modify_message(service, 'me', message_id, add_labels=['IMPORTANT'])
    elif choice == '2':
        result = modify_message(service, 'me', message_id, remove_labels=['IMPORTANT'])
    elif choice == '3':
        result = modify_message(service, 'me', message_id, remove_labels=['UNREAD'])
    elif choice == '4':
        result = modify_message(service, 'me', message_id, add_labels=['UNREAD'])
    else:
        logger.error("Invalid choice")
        return
    
    if result:
        print("\nMessage modified successfully!")
        print(f"New labels: {', '.join(result.get('labelIds', []))}")
    else:
        print("\nFailed to modify message.")

def list_threads(service, user_id='me', query='', max_results=10):
    """List threads in the user's mailbox.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        query: Search query (same format as Gmail search box).
        max_results: Maximum number of threads to return.
        
    Returns:
        List of threads.
    """
    try:
        logger.debug(f"Listing threads for user {user_id} with query: {query}")
        
        # Get thread list
        response = service.users().threads().list(
            userId=user_id,
            q=query,
            maxResults=max_results
        ).execute()
        
        threads = response.get('threads', [])
        logger.info(f"Found {len(threads)} threads matching query")
        
        return threads
    except HttpError as error:
        logger.error(f"Error listing threads: {error}", exc_info=True)
        return []

def get_thread(service, user_id, thread_id, format='metadata'):
    """Get a specific thread with all its messages.
    
    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me'.
        thread_id: ID of the thread to retrieve.
        format: Format of the messages (metadata, minimal, raw, full).
               Note: 'full' requires more permissions than 'metadata'.
        
    Returns:
        The specified thread with all its messages.
    """
    try:
        logger.debug(f"Getting thread {thread_id} for user {user_id}")
        
        # Handle potential permission issues with format
        try:
            thread = service.users().threads().get(
                userId=user_id,
                id=thread_id,
                format=format
            ).execute()
        except HttpError as error:
            # If we get a permission error with 'full' format, try with 'metadata'
            if format == 'full' and "Metadata scope doesn't allow format FULL" in str(error):
                logger.warning("Permission denied for 'full' format, falling back to 'metadata'")
                thread = service.users().threads().get(
                    userId=user_id,
                    id=thread_id,
                    format='metadata'
                ).execute()
            else:
                # If it's a different error, re-raise it
                raise
        
        logger.info(f"Successfully retrieved thread {thread_id} with {len(thread.get('messages', []))} messages")
        return thread
    except HttpError as error:
        logger.error(f"Error getting thread: {error}", exc_info=True)
        return None

def test_gmail_list_threads():
    """Test listing Gmail threads."""
    logger.info("=== Testing Gmail List Threads API ===")
    
    # Authenticate and build service
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user input for search query
    query = input("Enter search query (press Enter for all threads): ")
    max_results = int(input("Maximum number of threads to retrieve (default: 5): ") or "5")
    
    # List threads
    threads = list_threads(service, query=query, max_results=max_results)
    
    if not threads:
        logger.info("No threads found matching the query")
        return
    
    # Display the thread information
    print(f"\nFound {len(threads)} threads:")
    for i, thread in enumerate(threads):
        # Get the first message in each thread to display the subject
        thread_data = get_thread(service, 'me', thread['id'], format='metadata')
        
        if not thread_data or 'messages' not in thread_data or not thread_data['messages']:
            subject = "Unknown subject"
        else:
            # Try to get the subject from the first message
            subject = "No subject"
            first_msg = thread_data['messages'][0]
            if 'payload' in first_msg and 'headers' in first_msg['payload']:
                for header in first_msg['payload']['headers']:
                    if header['name'] == 'Subject':
                        subject = header['value']
                        break
        
        print(f"{i+1}. {subject[:50]}... ({len(thread_data.get('messages', []))} messages) [ID: {thread['id']}]")

def test_gmail_get_thread():
    """Test retrieving a specific Gmail thread."""
    logger.info("=== Testing Gmail Get Thread API ===")
    
    # Authenticate and build service
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    
    # First list some threads to choose from
    test_gmail_list_threads()
    
    # Get thread ID from user
    thread_id = input("\nEnter the thread ID to retrieve: ")
    if not thread_id:
        logger.error("No thread ID provided")
        return
    
    # Get format preference
    format_pref = input("\nUse 'metadata' or 'full' format? (default: metadata): ").lower()
    if format_pref not in ['metadata', 'full']:
        format_pref = 'metadata'
    
    if format_pref == 'full':
        print("Note: 'full' format requires additional permissions and may fail with a permission error.")
    
    # Get the thread
    thread = get_thread(service, 'me', thread_id, format=format_pref)
    
    if not thread:
        logger.error(f"Could not retrieve thread with ID: {thread_id}")
        return
    
    # Display the conversation
    print(f"\n=== Conversation Thread (ID: {thread_id}) ===")
    print(f"Total messages: {len(thread.get('messages', []))}")
    
    for i, message in enumerate(thread.get('messages', [])):
        # Extract headers
        headers = {}
        if 'payload' in message and 'headers' in message['payload']:
            for header in message['payload']['headers']:
                if header['name'] in ['Subject', 'From', 'To', 'Date']:
                    headers[header['name']] = header['value']
        
        # Display message details
        print(f"\nMessage {i+1}:")
        print(f"From: {headers.get('From', 'Unknown')}")
        print(f"Date: {headers.get('Date', 'Unknown')}")
        print(f"Subject: {headers.get('Subject', 'No subject')}")
        print(f"Snippet: {message.get('snippet', '')}")
        print("-" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail API Test")
    parser.add_argument("--send", action="store_true", help="Test sending an email")
    parser.add_argument("--modify", action="store_true", help="Test modifying email labels")
    parser.add_argument("--list-threads", action="store_true", help="Test listing threads")
    parser.add_argument("--get-thread", action="store_true", help="Test retrieving a specific thread")
    
    args = parser.parse_args()
    
    if args.send:
        test_gmail_send()
    elif args.modify:
        test_gmail_modify()
    elif args.list_threads:
        test_gmail_list_threads()
    elif args.get_thread:
        test_gmail_get_thread()
    else:
        print("Please specify a test to run:")
        print("  --send         Test sending an email")
        print("  --modify       Test modifying email labels")
        print("  --list-threads Test listing email threads")
        print("  --get-thread   Test retrieving a specific thread")
        parser.print_help()
