# -*- coding: utf-8 -*-
"""模型层基础适配器"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseModelAdapter(ABC):
    """大模型API统一接口"""

    def __init__(self, model_id: str, config: dict):
        self.model_id = model_id
        self.display_name = config.get("display_name", model_id)
        self.model = config["model"]
        self.base_url = config["base_url"]
        self.api_key = self._resolve_key(config["api_key_env"])
        self.client = self._create_client()

    def _resolve_key(self, env_name: str) -> str:
        import os
        key = os.getenv(env_name, "")
        if not key or key.startswith("your_"):
            raise ValueError(
                f"API Key 未配置: 请在 .env 文件中设置 {env_name}"
            )
        return key

    def _create_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        """
        发送对话请求并返回结构化结果。

        Returns:
            {
                "model": str,
                "content": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int},
                "latency_ms": float,
            }
        """
        import time

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = (time.time() - start) * 1000

        choice = response.choices[0]
        usage = response.usage

        return {
            "model": self.model_id,
            "content": choice.message.content.strip(),
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            },
            "latency_ms": round(latency, 1),
        }
