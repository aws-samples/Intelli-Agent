from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from common_logic.common_utils.constant import LLMModelType, EmbeddingModelType


@dataclass
class ModelConfig:
    model_id: str
    default_model_kwargs: Dict[str, Any] = None
    enable_any_tool_choice: bool = True
    any_tool_choice_value: str = "any"
    enable_prefill: bool = True

    def __post_init__(self):
        if self.default_model_kwargs is None:
            self.default_model_kwargs = {}


BASE_CONFIG = ModelConfig(
    model_id=LLMModelType.CLAUDE_3_SONNET,
    default_model_kwargs={"max_tokens": 1000,
                          "temperature": 0.01, "top_p": 0.9},
)

CLAUDE_MODEL_CONFIG = [
    BASE_CONFIG,
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_HAIKU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_SONNET_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_OPUS_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_HAIKU_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_SONNET_V2_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_HAIKU_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_SONNET_EU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_SONNET_EU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_HAIKU_EU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_SONNET_APAC,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_SONNET_APAC,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_HAIKU_APAC,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_SONNET_V2,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_3_5_HAIKU,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_2,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
    ModelConfig(
        model_id=LLMModelType.CLAUDE_21,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
    ),
]

NOVA_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.NOVA_PRO,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.NOVA_LITE,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.NOVA_MICRO,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
]

MISTRAL_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        default_model_kwargs={"max_tokens": 4096, "temperature": 0.01}
    ),
    ModelConfig(
        model_id=LLMModelType.MISTRAL_LARGE_2407,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_prefill=False
    ),
]

LLAMA_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.LLAMA3_1_70B_INSTRUCT,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.LLAMA3_1_70B_INSTRUCT_US,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.LLAMA3_2_90B_INSTRUCT,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    )
]

CORHERE_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.COHERE_COMMAND_R_PLUS,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=False
    ),
]

BEDROCK_MODEL_CONFIGS = CLAUDE_MODEL_CONFIG + NOVA_MODEL_CONFIGS + \
    MISTRAL_MODEL_CONFIGS + LLAMA_MODEL_CONFIGS + CORHERE_MODEL_CONFIGS


QWEN25_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.QWEN25_INSTRUCT_72B_AWQ,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=True,
        enable_prefill=True
    ),
    ModelConfig(
        model_id=LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_70B,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=True
    ),
    ModelConfig(
        model_id=LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_8B,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=True
    ),
    ModelConfig(
        model_id=LLMModelType.DEEPSEEK_R1_DISTILL_QWEN_32B,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=False,
        enable_prefill=True
    )
]


OPENAI_MODEL_CONFIGS = [
    ModelConfig(
        model_id=LLMModelType.GPT4O20240806,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=True,
        any_tool_choice_value="required",
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.GPT3D5TURBO0125,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=True,
        any_tool_choice_value="required",
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.GPT4OMINI20240718,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=True,
        any_tool_choice_value="required",
        enable_prefill=False
    ),
    ModelConfig(
        model_id=LLMModelType.GPT4TURBO20240409,
        default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
        enable_any_tool_choice=True,
        any_tool_choice_value="required",
        enable_prefill=False
    ),
]


# Embedding model configs

@dataclass
class EmbeddingModelConfig:
    model_id: Union[str, None] = None
    default_model_kwargs: Dict[str, Any] = None


OPENAI_EMBEDDING_CONFIG = [
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.OPENAI_TEXT_EMBEDDING_3_SMALL,
        default_model_kwargs={"dimensions": 1536}
    ),
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.OPENAI_TEXT_EMBEDDING_3_LARGE,
        default_model_kwargs={"dimensions": 3072}
    ),
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.OPENAI_TEXT_EMBEDDING_ADA_002,
        default_model_kwargs={"dimensions": 1536}
    )
]

AMAZON_TITAN_EMBEDDING_CONFIGS = [
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.AMAZON_TITAN_V1,
        # default_model_kwargs={"dimensions": 1536}

    ),
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.AMAZON_TITAN_V2,
        default_model_kwargs={"dimensions": 1024}
    ),
    # EmbeddingModelConfig(
    #     model_id=EmbeddingModelType.AMAZON_TITAN_IMAGE,
    #     # default_model_kwargs={"dimensions": 1024}
    # )

]

COHERE_EMBEDDING_CONFIGS = [
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.COHERE_EMBED_ENGLISH_V3,
        # default_model_kwargs={"dimensions": 1024}
    ),
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.COHERE_EMBED_MULTILINGUAL_V3,
        default_model_kwargs={"dimensions": 1024}
    )
]

BEDROCK_EMBEDDING_CONFIGS = AMAZON_TITAN_EMBEDDING_CONFIGS + COHERE_EMBEDDING_CONFIGS


BCE_EMBEDDING_CONFIGS = [
    EmbeddingModelConfig(
        model_id=EmbeddingModelType.BCE_EMBEDDING,
        # default_model_kwargs={"dimensions": 768}
    )
]


# MODEL_CONFIGS = {
# LLMModelType.CLAUDE_3_SONNET: BASE_CONFIG,
# LLMModelType.CLAUDE_3_HAIKU: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_HAIKU,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_SONNET_US: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_SONNET_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_OPUS_US: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_OPUS_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_HAIKU_US: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_HAIKU_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_SONNET_V2_US: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_SONNET_V2_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_HAIKU_US: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_HAIKU_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_SONNET_EU: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_SONNET_EU,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_SONNET_EU: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_SONNET_EU,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_HAIKU_EU: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_HAIKU_EU,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_SONNET_APAC: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_SONNET_APAC,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_SONNET_APAC: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_SONNET_APAC,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_HAIKU_APAC: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_HAIKU_APAC,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_SONNET_V2: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_SONNET_V2,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_3_5_HAIKU: ModelConfig(
#     model_id=LLMModelType.CLAUDE_3_5_HAIKU,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_2: ModelConfig(
#     model_id=LLMModelType.CLAUDE_2,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.CLAUDE_21: ModelConfig(
#     model_id=LLMModelType.CLAUDE_21,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy()
# ),
# LLMModelType.NOVA_PRO: ModelConfig(
#     model_id=LLMModelType.NOVA_PRO,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.NOVA_LITE: ModelConfig(
#     model_id=LLMModelType.NOVA_LITE,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.NOVA_MICRO: ModelConfig(
#     model_id=LLMModelType.NOVA_MICRO,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.MIXTRAL_8X7B_INSTRUCT: ModelConfig(
#     model_id=LLMModelType.MIXTRAL_8X7B_INSTRUCT,
#     default_model_kwargs={"max_tokens": 4096, "temperature": 0.01}
# ),
# LLMModelType.LLAMA3_1_70B_INSTRUCT: ModelConfig(
#     model_id=LLMModelType.LLAMA3_1_70B_INSTRUCT,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.LLAMA3_1_70B_INSTRUCT_US: ModelConfig(
#     model_id=LLMModelType.LLAMA3_1_70B_INSTRUCT_US,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.LLAMA3_2_90B_INSTRUCT: ModelConfig(
#     model_id=LLMModelType.LLAMA3_2_90B_INSTRUCT,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.MISTRAL_LARGE_2407: ModelConfig(
#     model_id=LLMModelType.MISTRAL_LARGE_2407,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_prefill=False
# ),
# LLMModelType.COHERE_COMMAND_R_PLUS: ModelConfig(
#     model_id=LLMModelType.COHERE_COMMAND_R_PLUS,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=False,
#     enable_prefill=False
# ),
# LLMModelType.QWEN25_INSTRUCT_72B_AWQ: ModelConfig(
#     model_id=LLMModelType.QWEN25_INSTRUCT_72B_AWQ,
#     default_model_kwargs=BASE_CONFIG.default_model_kwargs.copy(),
#     enable_any_tool_choice=True,
#     enable_prefill=True
# )
# }
