from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class KimiResult:
    intent: str
    reply: str


class KimiClient:
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
        normalized_model = model.strip().replace("“", "").replace("”", "").replace('"', "")
        if normalized_model.lower() == "kimi k3":
            normalized_model = "k3"
        self._model = normalized_model

    def infer_intent_and_reply(self, *, user_text: str) -> KimiResult:
        system_prompt = (
            "你是企业 IM 机器人中控。\n"
            "目标：对用户消息做意图识别，并给出一条简短、可直接发送的中文回复。\n"
            "输出必须是严格 JSON：{\"intent\": string, \"reply\": string}。\n"
            "intent 示例：问候/闲聊/询价/报错/知识问答/指令/其他。\n"
            "reply 要自然、简短，不要提及模型或 JSON。"
        )
        temperature = 0.2
        if self._model.startswith("k3") or "for-coding" in self._model:
            temperature = 1

        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("kimi response missing content")
        parsed = json.loads(content)
        intent = str(parsed.get("intent") or "其他")
        reply = str(parsed.get("reply") or "")
        return KimiResult(intent=intent, reply=reply)
