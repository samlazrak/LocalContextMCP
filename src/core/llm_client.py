"""LLM client for multiple providers."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

import aiohttp
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response format."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time_ms: int
    provider: str


@dataclass
class EmbeddingResponse:
    """Standardized embedding response format."""
    embedding: List[float]
    model: str
    usage: Dict[str, int]
    response_time_ms: int
    provider: str


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"{provider}: {message}")


class BaseLLMClient:
    """Base class for LLM clients."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make an HTTP request to the LLM API."""
        if not self.session:
            raise RuntimeError("Client session not initialized")
        
        url = f"{self.base_url}/{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.post(url, json=payload) as response:
                response_time_ms = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    data = await response.json()
                    data['_response_time_ms'] = response_time_ms
                    return data
                else:
                    error_text = await response.text()
                    raise LLMError(
                        f"HTTP {response.status}: {error_text}",
                        self.__class__.__name__,
                        response.status
                    )
        except aiohttp.ClientError as e:
            raise LLMError(f"Network error: {str(e)}", self.__class__.__name__)


class LMStudioClient(BaseLLMClient):
    """Client for LM Studio API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        super().__init__(base_url, timeout)
        self.provider = "lmstudio"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        response = await self._make_request("chat/completions", payload)
        
        choice = response["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=response["model"],
            usage=response.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            response_time_ms=response.get("_response_time_ms", 0),
            provider=self.provider
        )
    
    async def embedding(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        """Generate text embeddings."""
        payload = {
            "model": model,
            "input": text
        }
        
        response = await self._make_request("embeddings", payload)
        
        return EmbeddingResponse(
            embedding=response["data"][0]["embedding"],
            model=response["model"],
            usage=response.get("usage", {}),
            response_time_ms=response.get("_response_time_ms", 0),
            provider=self.provider
        )
    
    async def health_check(self) -> bool:
        """Check if LM Studio is responding."""
        try:
            response = await self._make_request("models", {})
            return "data" in response
        except Exception:
            return False


class DeepSeekClient(BaseLLMClient):
    """Client for DeepSeek API."""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: Optional[str] = None, 
        timeout: int = 60
    ):
        super().__init__(base_url, timeout)
        self.api_key = api_key
        self.provider = "deepseek"
    
    async def __aenter__(self):
        """Async context manager entry with auth headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=headers
        )
        return self
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 8192,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        response = await self._make_request("chat/completions", payload)
        
        choice = response["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=response["model"],
            usage=response.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            response_time_ms=response.get("_response_time_ms", 0),
            provider=self.provider
        )
    
    async def health_check(self) -> bool:
        """Check if DeepSeek is responding."""
        try:
            response = await self._make_request("models", {})
            return "data" in response
        except Exception:
            return False


class LLMManager:
    """Manages multiple LLM clients."""
    
    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[str, BaseLLMClient] = {}
    
    async def initialize(self) -> None:
        """Initialize all LLM clients."""
        # Initialize LM Studio client
        self._clients["lmstudio"] = LMStudioClient(
            self.settings.lmstudio.base_url,
            self.settings.lmstudio.timeout
        )
        
        # Initialize DeepSeek client if configured
        if self.settings.deepseek.base_url:
            self._clients["deepseek"] = DeepSeekClient(
                self.settings.deepseek.base_url,
                self.settings.deepseek.api_key,
                self.settings.deepseek.timeout
            )
        
        logger.info("LLM clients initialized", clients=list(self._clients.keys()))
    
    async def get_client(self, provider: str) -> BaseLLMClient:
        """Get a client by provider name."""
        if provider not in self._clients:
            raise ValueError(f"Unknown provider: {provider}")
        return self._clients[provider]
    
    async def chat_completion(
        self,
        prompt: str,
        provider: str = "lmstudio",
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion using the specified provider."""
        client = await self.get_client(provider)
        
        # Use default model if not specified
        if not model:
            if provider == "lmstudio":
                model = self.settings.lmstudio.model
            elif provider == "deepseek":
                model = self.settings.deepseek.model
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with client:
            return await client.chat_completion(messages, model, **kwargs)
    
    async def embedding(
        self,
        text: str,
        provider: str = "lmstudio",
        model: Optional[str] = None
    ) -> EmbeddingResponse:
        """Generate embeddings using the specified provider."""
        client = await self.get_client(provider)
        
        if not model:
            if provider == "lmstudio":
                model = self.settings.lmstudio.embedding_model
            else:
                raise ValueError(f"Embedding not supported for provider: {provider}")
        
        if not isinstance(client, LMStudioClient):
            raise ValueError(f"Embedding not supported for provider: {provider}")
        
        async with client:
            return await client.embedding(text, model)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all configured providers."""
        results = {}
        
        for provider, client in self._clients.items():
            try:
                async with client:
                    results[provider] = await client.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {provider}", error=str(e))
                results[provider] = False
        
        return results
    
    async def choose_best_provider(
        self, 
        task_type: str = "general",
        prefer_local: bool = True
    ) -> str:
        """Choose the best provider based on task type and health."""
        health_status = await self.health_check_all()
        
        # Filter to healthy providers
        healthy_providers = [p for p, healthy in health_status.items() if healthy]
        
        if not healthy_providers:
            raise LLMError("No healthy LLM providers available", "all")
        
        # Choose based on task type and preferences
        if task_type in ["code_generation", "complex_analysis"] and "deepseek" in healthy_providers:
            return "deepseek"
        elif "lmstudio" in healthy_providers and prefer_local:
            return "lmstudio"
        else:
            return healthy_providers[0]


# Global LLM manager instance
llm_manager = LLMManager()


async def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    return llm_manager


async def initialize_llm_clients() -> None:
    """Initialize LLM clients."""
    await llm_manager.initialize()


# Convenience functions
async def chat_completion(
    prompt: str,
    provider: Optional[str] = None,
    **kwargs
) -> LLMResponse:
    """Generate a chat completion with automatic provider selection."""
    if not provider:
        provider = await llm_manager.choose_best_provider()
    
    return await llm_manager.chat_completion(prompt, provider, **kwargs)


async def get_embedding(text: str, provider: str = "lmstudio") -> EmbeddingResponse:
    """Generate embeddings."""
    return await llm_manager.embedding(text, provider)