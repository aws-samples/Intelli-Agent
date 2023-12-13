import typing as t
from datasets import Dataset
import re

from langchain.embeddings import BedrockEmbeddings
from ragas.metrics import AnswerCorrectness
from ragas.metrics._answer_similarity import AnswerSimilarity
from .faithfulness import faithfulness


class ClaudeAnswerCorrectness(AnswerCorrectness):
    answer_similarity = BedrockEmbeddings()
    faithfulness = faithfulness

answer_correctness = ClaudeAnswerCorrectness()