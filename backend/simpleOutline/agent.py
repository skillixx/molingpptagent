import os
import random

from google.adk.agents import Agent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import BaseTool
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from create_model import create_model
from tools import DocumentSearch
from dotenv import load_dotenv
import prompt
from callbacks import after_model_callback, after_tool_callback, before_model_callback
load_dotenv()

class OutlineAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="outline_agent",
            model=create_model(model=os.environ["LLM_MODEL"], provider=os.environ["MODEL_PROVIDER"]),
            description="根据要求生成PPT大纲",
            instruction=self._get_dynamic_instruction,
            before_model_callback=before_model_callback,
            after_model_callback=after_model_callback,
            after_tool_callback=after_tool_callback,
            tools=[DocumentSearch],
            **kwargs
        )

    def _get_user_content_from_context(self, callback_context: CallbackContext) -> str | None:
        """
        获取用户的输入
        """
        # 1) 通过回调上下文的 user_content（如果该属性存在）
        user_content = getattr(callback_context, "user_content", None)
        if user_content and getattr(user_content, "parts", None):
            for part in user_content.parts:
                text = getattr(part, "text", None)
                if text:
                    return text
        return None

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        # 从metadata中获取language
        metadata = ctx.state.get("metadata", {})
        language = metadata.get("language", "chinese")  # 默认中文
        
        # 根据不同的情况选择不同的prompt
        user_input = self._get_user_content_from_context(ctx)
        # 根据不同的的输入长度，形成不同的prompt
        if len(user_input) > prompt.USER_INPUT_NUMBER:
            prompt_instruction = prompt.OUTLINE_INSTRUCTION_NO_SEARCH.format(language=language)
        else:
            prompt_instruction = prompt.OUTLINE_INSTRUCTION_WITH_SEARCH.format(language=language)
        return prompt_instruction

root_agent = OutlineAgent()
