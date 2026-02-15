import time
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from services.usage_stats import get_current_vision_context 

router = APIRouter(tags=["chat"])

class ChatMessage(BaseModel):
    user_id: str
    message: str


@router.post("/")
async def chat_endpoint(chat: ChatMessage, request: Request):
    # One line to get vision!
    vision_packet = get_current_vision_context(request, chat.user_id)
    
    response = await run_in_threadpool(
        request.app.state.brain.decide_response, 
        vision_data=vision_packet,
        prompt_text=chat.message
    )
    return {"response": response}


# import time
# from fastapi import APIRouter
# from fastapi.concurrency import run_in_threadpool
# from pydantic import BaseModel  


# router = APIRouter(prefix="/chat", tags=["chat"])

# # --- GLOBAL STATE ---
# system_state = {
#     "latest_emotion": "Neutral",
#     "face_detected": False,
#     "brain_busy": False,
# }

# brain = None
# # detector = None
# # video_service = None



# # --- 1. Chat Endpoint ---

# class ChatMessage(BaseModel):
#     user_id: str
#     message: str


# # ------- end point -------

# @router.post("/chat")
# async def chat_endpoint(chat: ChatMessage):
#     if system_state["brain_busy"]:
#         return {"response": "Thinking..."}
    
#     system_state["brain_busy"] = True
#     try:
#         vision_packet = {
#             "emotion": system_state["latest_emotion"],
#             "face_detected": system_state["face_detected"],
#             "timestamp": time.time()
#         }
        
#         response_text = await run_in_threadpool(
#             brain.decide_response, 
#             vision_data=vision_packet,
#             prompt_text=chat.message,
#             extra_context={}
#         )
#         return {"response": response_text}
#     except Exception as e:
#         print(f"❌ Chat Error: {e}")
#         return {"response": "Error processing chat."}
#     finally:
#         system_state["brain_busy"] = False
