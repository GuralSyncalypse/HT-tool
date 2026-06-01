from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from redis import Redis
from rq import Queue
from tasks import run_selenium_task


app = FastAPI()
templates = Jinja2Templates(directory="templates")

redis_conn = Redis(host="localhost", port=6379)
queue = Queue(connection=redis_conn)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.post("/run-bot")
def run_bot():
    job = queue.enqueue(run_selenium_task)
    return {
        "status": "queued",
        "job_id": job.id
    }