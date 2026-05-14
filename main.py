import uvicorn

if __name__ == "__main__":
    uvicorn.run("vcm_os.app.api:app", host="0.0.0.0", port=8123, reload=False)
