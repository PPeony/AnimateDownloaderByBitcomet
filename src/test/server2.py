from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI()


# Simulate a simple LLM tool to answer questions
def simple_llm_tool(question: str) -> str:
    if "your name" in question.lower():
        return "I am an LLM powered server."
    elif "capital" in question.lower():
        return "The capital of France is Paris."
    elif "weather" in question.lower():
        return "I cannot check the weather, but I can help you with coding!"
    else:
        return "Sorry, I don't have an answer to that."


# Define the request model using Pydantic
class QuestionRequest(BaseModel):
    question: str


# Define the response model
class QuestionResponse(BaseModel):
    status: str
    question: str
    answer: str


@app.post("/mcp", response_model=QuestionResponse)
async def mcp_server(request: QuestionRequest):
    try:
        # Use the simulated LLM tool to answer the question
        answer = simple_llm_tool(request.question)

        return QuestionResponse(
            status="success",
            question=request.question,
            answer=answer
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
