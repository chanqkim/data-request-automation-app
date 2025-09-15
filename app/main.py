from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import auth, menu, data_extraction

app = FastAPI(title="Data Request Automation Portal")

# registering routers
app.include_router(auth.router)


# Router for data-extraction-automation-app menu page
app.include_router(menu.router)


# Router for the page handling data extraction and automated Jira data uploads
app.include_router(data_extraction.router, tags=["Data Extraction"])


# land to login page
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login")


# check health
@app.get("/health")
def health_check():
    return {"status": "data-request-automation-app is active"}
