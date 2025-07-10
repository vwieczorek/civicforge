"""
LLM Provider Interface

Defines the protocol for Large Language Model integration,
preparing for future advanced NLP capabilities.
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class LLMCapability(Enum):
    """Capabilities that an LLM provider might support"""
    TEXT_GENERATION = "text_generation"
    EMBEDDINGS = "embeddings"
    CHAT = "chat"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"


@dataclass
class LLMResponse:
    """Response from an LLM provider"""
    text: str
    model: str
    usage: Dict[str, int]  # tokens used, etc.
    metadata: Dict[str, Any] = None
    

class LLMProvider(Protocol):
    """
    Protocol for LLM provider operations.
    
    Future implementations will support:
    - Multiple LLM backends (OpenAI, Anthropic, local models)
    - Streaming responses
    - Function calling
    - Multi-modal inputs
    """
    
    def generate(self, 
                prompt: str,
                max_tokens: Optional[int] = None,
                temperature: float = 0.7,
                **kwargs) -> LLMResponse:
        """Generate text from a prompt"""
        ...
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding vector for text"""
        ...
    
    def chat(self,
            messages: List[Dict[str, str]],
            max_tokens: Optional[int] = None,
            **kwargs) -> LLMResponse:
        """Chat completion with conversation history"""
        ...
    
    def get_capabilities(self) -> List[LLMCapability]:
        """Get list of supported capabilities"""
        ...
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        ...


class MockLLMProvider:
    """
    Mock implementation for Phase 1 development.
    Returns simple responses for testing.
    """
    
    def __init__(self):
        self._call_count = 0
    
    def generate(self, 
                prompt: str,
                max_tokens: Optional[int] = None,
                temperature: float = 0.7,
                **kwargs) -> LLMResponse:
        """Return mock response"""
        self._call_count += 1
        
        # Simple mock responses based on prompt content
        if "summarize" in prompt.lower():
            response = "This is a mock summary of the provided content."
        elif "explain" in prompt.lower():
            response = "This is a mock explanation of the concept."
        else:
            response = "This is a mock LLM response."
            
        return LLMResponse(
            text=response,
            model="mock-gpt",
            usage={"prompt_tokens": 10, "completion_tokens": 20}
        )
    
    def create_embedding(self, text: str) -> List[float]:
        """Return mock embedding"""
        # Simple hash-based mock embedding
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Generate 384-dimensional vector (like all-MiniLM-L6-v2)
        return [(hash_val >> i) & 1 for i in range(384)]
    
    def chat(self,
            messages: List[Dict[str, str]],
            max_tokens: Optional[int] = None,
            **kwargs) -> LLMResponse:
        """Return mock chat response"""
        last_message = messages[-1]["content"] if messages else ""
        return self.generate(last_message, max_tokens, **kwargs)
    
    def get_capabilities(self) -> List[LLMCapability]:
        """Return mock capabilities"""
        return [
            LLMCapability.TEXT_GENERATION,
            LLMCapability.EMBEDDINGS,
            LLMCapability.CHAT
        ]
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate"""
        # Approximate: 1 token per 4 characters
        return len(text) // 4