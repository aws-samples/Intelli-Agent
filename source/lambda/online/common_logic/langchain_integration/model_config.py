from dataclasses import dataclass
from typing import Dict, Any, Optional
from common_logic.common_utils.constant import LLMModelType


@dataclass
class ModelConfig:
    model_id: str
    default_model_kwargs: Dict[str, Any] = None

    def __post_init__(self):
        if self.default_model_kwargs is None:
            self.default_model_kwargs = {}


BASE_CONFIG = ModelConfig(
    model_id=LLMModelType.CLAUDE_3_SONNET,
    default_model_kwargs={"max_tokens": 1000, "temperature": 0.01},
)

MODEL_CONFIGS = {
    LLMModelType.CLAUDE_3_SONNET: BASE_CONFIG,
    LLMModelType.CLAUDE_3_HAIKU: ModelConfig(
        model_id=LLMModelType.CLAUDE_3_HAIKU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.CLAUDE_3_5_SONNET_V2: ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_SONNET_V2,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.CLAUDE_3_5_HAIKU: ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_HAIKU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.CLAUDE_2: ModelConfig(
        model_id=LLMModelType.CLAUDE_2,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.CLAUDE_21: ModelConfig(
        model_id=LLMModelType.CLAUDE_21,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.NOVA_PRO: ModelConfig(
        model_id=LLMModelType.NOVA_PRO,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.MIXTRAL_8X7B_INSTRUCT: ModelConfig(
        model_id=LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        default_model_kwargs={"max_tokens": 4096, "temperature": 0.01}
    ),
    LLMModelType.LLAMA3_1_70B_INSTRUCT: ModelConfig(
        model_id=LLMModelType.LLAMA3_1_70B_INSTRUCT,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.LLAMA3_2_90B_INSTRUCT: ModelConfig(
        model_id=LLMModelType.LLAMA3_2_90B_INSTRUCT,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.MISTRAL_LARGE_2407: ModelConfig(
        model_id=LLMModelType.MISTRAL_LARGE_2407,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    LLMModelType.COHERE_COMMAND_R_PLUS: ModelConfig(
        model_id=LLMModelType.COHERE_COMMAND_R_PLUS,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    )
}
