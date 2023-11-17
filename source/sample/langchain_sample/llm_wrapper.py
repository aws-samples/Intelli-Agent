import io
import json

from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain.schema.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)

from langchain.chat_models.base import BaseChatModel
from csdc_llm import CSDCLLMBase
from langchain.pydantic_v1 import Extra
from langchain.schema.messages import AIMessage, BaseMessage
from langchain.schema.output import ChatGeneration, ChatGenerationChunk, ChatResult

from langchain.llms.utils import enforce_stop_tokens


class ChatPromptAdapter:
    """Adapter class to prepare the inputs from Langchain to prompt format
    that Chat model expects.
    """
    def _convert_one_message_to_text(
        self,
        message: BaseMessage,
        human_prompt: str,
        ai_prompt: str,
        system_prompt: str,
    ) -> str:
        if isinstance(message, ChatMessage):
            message_text = f"\n\n{message.role.capitalize()}: {message.content}"
        elif isinstance(message, HumanMessage):
            message_text = f"{human_prompt} {message.content}"
        elif isinstance(message, AIMessage):
            message_text = f"{ai_prompt} {message.content}"
        elif isinstance(message, SystemMessage):
            context = ''.join(message.content.split('\n----------------\n')[1:])
            message_text = system_prompt.format(context = context)
        else:
            raise ValueError(f"Got unknown type {message}")
        return message_text

    def convert_messages_to_prompt_CSDC(
        self,
        messages: List[BaseMessage],
        *,
        human_prompt: str = "<s><|User|>:",
        ai_prompt: str = "<|Bot|>:",
        system_prompt: str = "<|System|>:",
    ) -> str:
        """Format a list of messages into a full prompt for the CSDC Chat model
        Args:
            messages (List[BaseMessage]): List of BaseMessage to combine.
            human_prompt (str, optional): Human prompt tag. Defaults to "<s><|User|>:".
            ai_prompt (str, optional): AI prompt tag. Defaults to "<|Bot|>:".
            system_prompt (str, optional): System prompt tag. Defaults to "<|System|>:".
        Returns:
            str: Combined string with necessary human_prompt and ai_prompt tags.
        """

        messages = messages.copy()  # don't mutate the original list
        system_prompt = '以下context xml tag内的文本内容为背景知识：\n<context>\n{context}\n</context>\n请根据背景知识, 回答这个问题：'

        text = "".join(
            self._convert_one_message_to_text(message, human_prompt = '', ai_prompt = '', system_prompt = system_prompt)
            for message in messages
        )

        # trim off the trailing ' ' that might come from the "Assistant: "
        return text.rstrip()

    @classmethod
    def convert_messages_to_prompt(
        cls, provider: str, messages: List[BaseMessage], **kwargs: Any
    ) -> str:
        if provider == "CSDC":
            prompt = cls().convert_messages_to_prompt_CSDC(messages=messages, **kwargs)
        else:
            raise NotImplementedError(
                f"Provider {provider} model does not support chat."
            )
        return prompt

class LineIterator:
    """
    A helper class for parsing the byte stream input.

    The output of the model will be in the following format:

    b'{"outputs": [" a"]}\n'
    b'{"outputs": [" challenging"]}\n'
    b'{"outputs": [" problem"]}\n'
    ...

    While usually each PayloadPart event from the event stream will
    contain a byte array with a full json, this is not guaranteed
    and some of the json objects may be split acrossPayloadPart events.

    For example:

    {'PayloadPart': {'Bytes': b'{"outputs": '}}
    {'PayloadPart': {'Bytes': b'[" problem"]}\n'}}


    This class accounts for this by concatenating bytes written via the 'write' function
    and then exposing a method which will return lines (ending with a '\n' character)
    within the buffer via the 'scan_lines' function.
    It maintains the position of the last read position to ensure
    that previous bytes are not exposed again.

    For more details see:
    https://aws.amazon.com/blogs/machine-learning/elevating-the-generative-ai-experience-introducing-streaming-support-in-amazon-sagemaker-hosting/
    """

    def __init__(self, stream: Any) -> None:
        self.byte_iterator = iter(stream)
        self.buffer = io.BytesIO()
        self.read_pos = 0

    def __iter__(self) -> "LineIterator":
        return self

    def __next__(self) -> Any:
        while True:
            self.buffer.seek(self.read_pos)
            line = self.buffer.readline()
            if line and line[-1] == ord("\n"):
                self.read_pos += len(line)
                return line[:-1]
            try:
                chunk = next(self.byte_iterator)
            except StopIteration:
                if self.read_pos < self.buffer.getbuffer().nbytes:
                    continue
                raise
            if "PayloadPart" not in chunk:
                # Unknown Event Type
                continue
            self.buffer.seek(0, io.SEEK_END)
            self.buffer.write(chunk["PayloadPart"]["Bytes"])


class ChatCSDC(BaseChatModel, CSDCLLMBase):
    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "aws_csdc_chat"

    # class Config:
    #     """Configuration for this pydantic object."""

    #     extra = Extra.forbid

    def _invoke(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        provider = self._get_provider()

        prompt = ChatPromptAdapter.convert_messages_to_prompt(
            provider=provider, messages=messages
        )

        params: Dict[str, Any] = {**kwargs}
        if stop:
            params["stop_sequences"] = stop

        completion = self._prepare_input_and_invoke(
            prompt=prompt, stop=stop, run_manager=run_manager, **params
        )

        message = AIMessage(content=completion)
        return ChatResult(generations=[ChatGeneration(message=message)])
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        provider = self._get_provider()

        prompt = ChatPromptAdapter.convert_messages_to_prompt(
            provider=provider, messages=messages
        )

        params: Dict[str, Any] = {**kwargs}
        if stop:
            params["stop_sequences"] = stop

        resp = self._prepare_input_and_invoke_stream(
            prompt=prompt, stop=stop, run_manager=run_manager, **params
        )

        iterator = LineIterator(resp["Body"])
        current_completion: str = ""
        for line in iterator:
            resp = json.loads(line)
            resp_output = resp.get("outputs")["outputs"]
            if stop is not None:
                # Uses same approach as below
                resp_output = enforce_stop_tokens(resp_output, stop)
            message_chunk = AIMessageChunk(content=resp_output)
            yield ChatGenerationChunk(message=message_chunk, generations = "")
            # current_completion += resp_output
            run_manager.on_llm_new_token(resp_output)
        

    def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        raise NotImplementedError(
            """CSDC Chat doesn't support async requests at the moment."""
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        streaming = self._get_streaming()
        print(f"+++++++++++ streaming is: {streaming}")
        completion = ""
        if streaming:
            for chunk in self._stream(messages, stop, run_manager, **kwargs):
                completion += chunk.text
            message = AIMessage(content=completion)
            return ChatResult(generations=[ChatGeneration(message=message)])
        else:
            return self._invoke(
                messages=messages, stop=stop, run_manager=run_manager, **kwargs
            )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            """CSDC Chat doesn't support async stream requests at the moment."""
        )