import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "::"),
        port=int(os.environ.get("PORT", "8000")),
    )
