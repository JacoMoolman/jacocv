import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from the .env file
load_dotenv()

app = FastAPI()

# Add CORS middleware
origins = [
    "https://jacomoolman.co.za",  # Your WordPress site
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow requests from this origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Define a Pydantic model for the request body
class Query(BaseModel):
    content: str

# Fetch the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise HTTPException(status_code=500, detail="OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=api_key)

# Email configurations
email_host = os.getenv("EMAIL_HOST")
email_port = int(os.getenv("EMAIL_PORT"))
email_user = os.getenv("EMAIL_HOST_USER")
email_password = os.getenv("EMAIL_HOST_PASSWORD")
email_recipient = os.getenv("EMAIL_RECIPIENT")

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL(email_host, email_port)  # Use SMTP_SSL for SSL connection
        server.login(email_user, email_password)
        text = msg.as_string()
        server.sendmail(email_user, email_recipient, text)
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/query/")
async def query_openai(query: Query):
    try:
        thread = client.beta.threads.create()
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=query.content
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id="asst_hcR1DhrSzthMdafP5EaTFME1",
            instructions="""You are here to give information about Jaco's CV and technical knowledge.
            If you cannot find information in the vector database and files uploaded, inform the user. Do not infer anything!
            IF DATA IS NOT AVAILABLE IN THE DOCUMENTS, INFORM THE USER OF THIS. DO NOT MAKE ANYTHING UP. DO NOT ASSUME ANYTHING. ONLY USE THE INFORMATION IN THE DOCUMENTS. NOTHING ELSE. ONLY INFO FROM THE DOCS.
            Before answering ANY question, confirm that the answer you give is in fact in the documentation!!!
            If you cannot find any information in the documentation, you MUST inform the user of this, stating that you cannot find the information in the documentation.
            When answering do you do NOT need to respond with "The documentation says this" or "According to the documentation etc". The user is aware that you are getting the information from the documentation.
            If the user asked you anything that is NOT related to Jaco's information please inform the user that you can only assist the task you have been given.
            Some information in the documentation will refer to Jaco in the first person as he wrote it himself. However, you should always refer to Jaco in the 3rd person.
            When the user refer to "you" or "your" etc. The user is in fact asking about Jaco and not "you" as in GPT.  Assume any "you", "your" etc refer to Jaco
            """
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            for message in messages:
                if message.role == 'assistant':
                    response = message.content[0].text.value
                    send_email(
                        subject="Query from your CV chatbot",
                        body=f"Query: {query.content}\nResponse: {response}"
                    )
                    return {"response": response}
        else:
            raise HTTPException(status_code=500, detail="OpenAI run did not complete successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
