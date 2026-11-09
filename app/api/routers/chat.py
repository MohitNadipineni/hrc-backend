import json

from fastapi.responses import StreamingResponse


from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import User, current_user
from app.repositories import threads
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, ThreadDetail, ThreadSummary
from app.services.chat import ThreadNotFound, handle_chat

router = APIRouter(prefix="/v1")


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: User = Depends(current_user)):
    thread_id = str(req.thread_id) if req.thread_id else None
    try:
        return handle_chat(user, req.question, thread_id)
    except ThreadNotFound:
        raise HTTPException(status_code=404, detail="Thread not found") from None


@router.get("/threads", response_model=list[ThreadSummary])
def list_my_threads(user: User = Depends(current_user)):
    return threads.list_threads(user.user_id)


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
def read_thread(thread_id: UUID, user: User = Depends(current_user)):
    thread = threads.get_thread(str(thread_id), user.user_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {**thread, "messages": threads.get_messages(str(thread_id))}


@router.delete("/threads/{thread_id}", status_code=204)
def delete_my_thread(thread_id: UUID, user: User = Depends(current_user)):
    if not threads.delete_thread(str(thread_id), user.user_id):
        raise HTTPException(status_code=404, detail="Thread not found")

@router.post("/chat/stream")
def chat_stream(req: ChatRequest, user: User = Depends(current_user)):
    thread_id = str(req.thread_id) if req.thread_id else None
    try:
        result = handle_chat(user, req.question, thread_id)
    except ThreadNotFound:
        raise HTTPException(status_code=404, detail="Thread not found") from None

    def events():
        meta = {k: result[k] for k in ("thread_id", "message_id", "route", "standalone_question")}
        yield f"event: meta\ndata: {json.dumps(meta, default=str)}\n\n"
        for word in result["answer"].split(" "):
            yield f"event: token\ndata: {json.dumps(word + ' ')}\n\n"
        done = {k: result[k] for k in ("citations", "sql", "warnings")}
        yield f"event: done\ndata: {json.dumps(done, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

@router.post("/feedback", status_code=204)
def give_feedback(req: FeedbackRequest, user: User = Depends(current_user)):
      if threads.answer_owner(req.message_id) != user.user_id:
          raise HTTPException(status_code=404, detail="Answer not found")
      threads.save_feedback(req.message_id, user.user_id, req.rating, req.comment)