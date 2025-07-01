"""
LLM client interface for MCP Server.
Supports multiple LLM providers with consistent interface.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass

import aiohttp
import httpx

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMMessage:
    """Represents a message in LLM conversation."""
    role: str  # user, assistant, system
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Represents response from LLM."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    response_time_ms: Optional[int] = None


@dataclass
class LLMStreamChunk:
    """Represents a streaming chunk from LLM."""
    content: str
    finish_reason: Optional[str] = None
    model: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[Union[aiohttp.ClientSession, httpx.AsyncClient]] = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the LLM provider."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the LLM provider."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """Complete a conversation."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        pass


class LMStudioProvider(LLMProvider):
    """LM Studio provider implementation."""
    
    async def initialize(self) -> None:
        """Initialize LM Studio client."""
        self.base_url = self.config.get("base_url", "http://localhost:1234/v1")
        self.default_model = self.config.get("model", "")
        self.timeout = self.config.get("timeout", 60)
        
        self.client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        logger.info("LM Studio provider initialized", base_url=self.base_url)
    
    async def close(self) -> None:
        """Close LM Studio client."""
        if self.client:
            await self.client.close()
    
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """Complete conversation with LM Studio."""
        if not self.client:
            raise RuntimeError("LM Studio provider not initialized")
        
        # Use default model if none specified
        if not model:
            model = self.default_model
        
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        start_time = time.time()
        
        try:
            if stream:
                return self._stream_completion(payload, start_time)
            else:
                return await self._complete_sync(payload, start_time)
                
        except Exception as e:
            logger.error("LM Studio completion failed", error=str(e), model=model)
            raise
    
    async def _complete_sync(self, payload: Dict[str, Any], start_time: float) -> LLMResponse:
        """Complete synchronous request."""
        async with self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload
        ) as response:
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"LM Studio API error {response.status}: {error_text}")
            
            data = await response.json()
            
            choice = data["choices"][0]
            
            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", payload["model"]),
                usage=data.get("usage"),
                finish_reason=choice.get("finish_reason"),
                response_time_ms=response_time
            )
    
    async def _stream_completion(
        self, payload: Dict[str, Any], start_time: float
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream completion chunks."""
        async with self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"LM Studio API error {response.status}: {error_text}")
            
            async for line in response.content:
                line = line.decode().strip()
                
                if line.startswith("data: "):
                    data_str = line[6:]
                    
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                        
                        if "content" in delta:
                            yield LLMStreamChunk(
                                content=delta["content"],
                                finish_reason=choice.get("finish_reason"),
                                model=data.get("model")
                            )
                    except json.JSONDecodeError:
                        continue
    
    async def health_check(self) -> Dict[str, Any]:
        """Check LM Studio health."""
        if not self.client:
            return {"status": "error", "message": "Client not initialized"}
        
        try:
            start_time = time.time()
            
            async with self.client.get(f"{self.base_url}/models") as response:
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    models = await response.json()
                    return {
                        "status": "healthy",
                        "response_time_ms": response_time,
                        "models": [model["id"] for model in models.get("data", [])]
                    }
                else:
                    return {
                        "status": "error", 
                        "message": f"API returned {response.status}"
                    }
                    
        except Exception as e:
            return {"status": "error", "message": str(e)}


class OllamaProvider(LLMProvider):
    """Ollama provider implementation."""
    
    async def initialize(self) -> None:
        """Initialize Ollama client."""
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.default_model = self.config.get("model", "")
        self.timeout = self.config.get("timeout", 60)
        
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info("Ollama provider initialized", base_url=self.base_url)
    
    async def close(self) -> None:
        """Close Ollama client."""
        if self.client:
            await self.client.aclose()
    
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """Complete conversation with Ollama."""
        if not self.client:
            raise RuntimeError("Ollama provider not initialized")
        
        # Use default model if none specified
        if not model:
            model = self.default_model
        
        # Build prompt from messages
        prompt = self._build_prompt(messages)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs
            }
        }
        
        start_time = time.time()
        
        try:
            if stream:
                return self._stream_completion(payload, start_time)
            else:
                return await self._complete_sync(payload, start_time)
                
        except Exception as e:
            logger.error("Ollama completion failed", error=str(e), model=model)
            raise
    
    def _build_prompt(self, messages: List[LLMMessage]) -> str:
        """Build prompt from messages for Ollama."""
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    async def _complete_sync(self, payload: Dict[str, Any], start_time: float) -> LLMResponse:
        """Complete synchronous request."""
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")
        
        data = response.json()
        
        return LLMResponse(
            content=data["response"],
            model=payload["model"],
            finish_reason="stop" if data.get("done") else None,
            response_time_ms=response_time
        )
    
    async def _stream_completion(
        self, payload: Dict[str, Any], start_time: float
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream completion chunks."""
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API error {response.status_code}")
            
            async for line in response.aiter_lines():
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield LLMStreamChunk(
                            content=data["response"],
                            finish_reason="stop" if data.get("done") else None,
                            model=payload["model"]
                        )
                        
                        if data.get("done"):
                            break
                            
                except json.JSONDecodeError:
                    continue
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama health."""
        if not self.client:
            return {"status": "error", "message": "Client not initialized"}
        
        try:
            start_time = time.time()
            
            response = await self.client.get(f"{self.base_url}/api/tags")
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "models": [model["name"] for model in data.get("models", [])]
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}


class LLMClient:
    """Main LLM client that manages multiple providers."""
    
    def __init__(self):
        self.config = get_config().llm
        self.providers: Dict[str, LLMProvider] = {}
        self.current_provider: Optional[str] = None
        
    async def initialize(self) -> None:
        """Initialize LLM client with configured providers."""
        # Initialize LM Studio provider
        if self.config.lmstudio_base_url:
            lmstudio_config = {
                "base_url": self.config.lmstudio_base_url,
                "model": self.config.lmstudio_model,
                "timeout": self.config.timeout
            }
            self.providers["lmstudio"] = LMStudioProvider(lmstudio_config)
            await self.providers["lmstudio"].initialize()
        
        # Initialize Ollama provider
        if self.config.ollama_base_url:
            ollama_config = {
                "base_url": self.config.ollama_base_url,
                "model": self.config.ollama_model,
                "timeout": self.config.timeout
            }
            self.providers["ollama"] = OllamaProvider(ollama_config)
            await self.providers["ollama"].initialize()
        
        # Set current provider
        self.current_provider = self.config.default_provider
        
        if self.current_provider not in self.providers:
            # Fallback to first available provider
            if self.providers:
                self.current_provider = list(self.providers.keys())[0]
            else:
                raise RuntimeError("No LLM providers configured")
        
        logger.info(
            "LLM client initialized",
            providers=list(self.providers.keys()),
            current_provider=self.current_provider
        )
    
    async def close(self) -> None:
        """Close all providers."""
        for provider in self.providers.values():
            await provider.close()
    
    async def complete(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]], str],
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Complete conversation using specified or current provider."""
        # Convert input to LLMMessage list
        llm_messages: List[LLMMessage]
        if isinstance(messages, str):
            llm_messages = [LLMMessage(role="user", content=messages)]
        elif isinstance(messages, list) and messages and isinstance(messages[0], dict):
            # Type cast to help linter understand this is a list of dicts
            dict_messages = messages  # type: List[Dict[str, str]]
            llm_messages = [LLMMessage(role=msg.get("role", "user"), content=msg.get("content", "")) for msg in dict_messages]
        else:
            llm_messages = messages  # type: List[LLMMessage]
        
        # Use specified provider or current default
        provider_name = provider or self.current_provider
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")
        
        provider_instance = self.providers[provider_name]
        
        logger.debug(
            "Completing LLM request",
            provider=provider_name,
            message_count=len(llm_messages)
        )
        
        # Ensure we get a sync response, not a stream
        kwargs["stream"] = False
        result = await provider_instance.complete(llm_messages, **kwargs)
        
        # Type guard to ensure we return LLMResponse
        if isinstance(result, LLMResponse):
            return result
        else:
            raise RuntimeError("Expected LLMResponse but got stream")
    
    async def stream_complete(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]], str],
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream completion using specified or current provider."""
        # Convert input to LLMMessage list
        if isinstance(messages, str):
            messages = [LLMMessage(role="user", content=messages)]
        elif isinstance(messages, list) and messages and isinstance(messages[0], dict):
            messages = [LLMMessage(**msg) for msg in messages]
        
        # Use specified provider or current default
        provider_name = provider or self.current_provider
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")
        
        provider_instance = self.providers[provider_name]
        
        # Enable streaming
        kwargs["stream"] = True
        
        logger.debug(
            "Starting LLM stream",
            provider=provider_name,
            message_count=len(messages)
        )
        
        async for chunk in await provider_instance.complete(messages, **kwargs):
            yield chunk
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all providers."""
        health_status = {
            "current_provider": self.current_provider,
            "providers": {}
        }
        
        for name, provider in self.providers.items():
            health_status["providers"][name] = await provider.health_check()
        
        return health_status
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self.providers.keys())
    
    def set_current_provider(self, provider: str) -> None:
        """Set the current default provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not available")
        
        self.current_provider = provider
        logger.info("Current LLM provider changed", provider=provider)


# Global LLM client instance
llm_client = LLMClient()


async def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    return llm_client