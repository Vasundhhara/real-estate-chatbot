import os
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from response import generate_response

app = FastAPI()

class QueryRequest(BaseModel):
    user_id: str
    question: str
    jwt: str
    
class AnswerResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=AnswerResponse)
async def chat_with_bot(query: QueryRequest):
    user_id = query.user_id
    user_query = query.question
    jwt_token = query.jwt

    response = generate_response(user_query, user_id, jwt_token)
    return AnswerResponse(answer=response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)





