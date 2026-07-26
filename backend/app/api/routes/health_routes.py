from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "service": "misconceptionos-backend"
        },
        "message": "Backend is running"
    }