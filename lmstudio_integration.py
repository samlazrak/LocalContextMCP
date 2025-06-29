import lmstudio as lms
from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Optional

# --- Model Management ---

def get_model(model_name: Optional[str] = None):
    """Get the current loaded model or load a specific one."""
    if model_name:
        return lms.llm(model_name)
    return lms.llm()

# --- Chat/Completion ---

def chat(prompt: str, model_name: Optional[str] = None) -> str:
    model = get_model(model_name)
    response = model.respond(prompt)
    return response.text

def complete(prompt: str, model_name: Optional[str] = None) -> str:
    model = get_model(model_name)
    completion = model.complete(prompt)
    return completion.text

# --- Embeddings ---

def get_embedding(text: str, model_name: Optional[str] = None) -> List[float]:
    model = get_model(model_name)
    return model.embed(text)

# --- Structured Output with Pydantic ---

def structured_respond_pydantic(prompt: str, schema: BaseModel, model_name: Optional[str] = None) -> Any:
    model = get_model(model_name)
    result = model.respond(prompt, response_format=schema)
    return result.parsed

# --- Structured Output with JSON Schema ---

def structured_respond_jsonschema(prompt: str, schema: dict, model_name: Optional[str] = None) -> Any:
    model = get_model(model_name)
    result = model.respond(prompt, response_format=schema)
    return result.parsed

# --- Agentic Tool Use ---

def agentic_act(prompt: str, tools: List[Callable], model_name: Optional[str] = None, on_message: Optional[Callable] = print):
    model = get_model(model_name)
    return model.act(prompt, tools, on_message=on_message)

# --- Example: Expose MCP tools as agentic tools ---

def mcp_tool_call(tool: str, params: Dict) -> Dict:
    # Import your MCP tool logic here, e.g. from mcp_server import tools_call
    # from mcp_server import tools_call
    # return tools_call(tool, params)
    return {"tool": tool, "params": params, "result": "stub"}

# Example usage:
if __name__ == "__main__":
    # Chat
    print(chat("Hello, world!"))

    # Completion
    print(complete("Once upon a time,"))

    # Embedding
    print(get_embedding("This is a test sentence."))

    # Structured output with Pydantic
    class BookSchema(BaseModel):
        title: str
        author: str
        year: int
    print(structured_respond_pydantic("Tell me about The Hobbit", BookSchema))

    # Structured output with JSON schema
    book_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "author": {"type": "string"},
            "year": {"type": "integer"}
        },
        "required": ["title", "author", "year"]
    }
    print(structured_respond_jsonschema("Tell me about The Hobbit", book_schema))

    # Agentic tool use
    def multiply(a: float, b: float) -> float:
        return a * b
    agentic_act("What is the result of 12345 multiplied by 54321?", [multiply])

    # Agentic tool use with MCP tool call stub
    agentic_act("Use the 'git' tool to get the current status.", [mcp_tool_call]) 