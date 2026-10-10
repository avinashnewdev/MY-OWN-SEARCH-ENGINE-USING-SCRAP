import time
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from engine import SearchEngineCore

app = FastAPI(
    title="MY OWN SEARCH ENGINE",
    description="High-performance search backend matching modern production architecture."
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_engine = SearchEngineCore()

@app.get("/api/search")
async def search_endpoint(q: str = Query(..., min_length=1, description="Search query")):
    start_time = time.time()
    try:
        data = await search_engine.execute_search(q)
        execution_time = round(time.time() - start_time, 3)
        return {
            "status": "success",
            "query": q,
            "search_time_seconds": execution_time,
            "total_results": data["total"],
            "instant_answer": data["instant_answer"],
            "results": data["results"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend directory for single-command run
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Local production server: http://127.0.0.1:8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
