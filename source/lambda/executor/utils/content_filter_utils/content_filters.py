import os 
import csv
from typing import Iterable,Union
abs_dir = os.path.dirname(__file__)


class ContentFilterBase:
    def filter_sentence(self,sentence:str):
        raise NotImplementedError


class MarketContentFilter(ContentFilterBase):
    def __init__(
            self,
            sensitive_words_path=os.path.join(abs_dir,'sensitive_word.csv')
            ) -> None:
        self.sensitive_words = self.create_sensitive_words(sensitive_words_path)

    def create_sensitive_words(self,sensitive_words_path):
        sensitive_words = set()
        with open(sensitive_words_path, mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                sensitive_words.add(row[0])
        return sensitive_words

    def filter_sensitive_words(self,sentence):
        for sensitive_word in self.sensitive_words:
            length = len(sensitive_word)
            sentence = sentence.replace(sensitive_word, '*' * length)
        return sentence
    
    def rebranding_words(self,sentence:str):
        rebranding_dict = {'AWS': '亚马逊云科技'}
        for key, value in rebranding_dict.items():
            sentence = sentence.replace(key, value)
        return sentence

    def filter_source(self, sources:list[str]):
        filtered_sources = []
        for source in sources:
            if source.startswith("http") and source.endswith(".html"):
                filtered_sources.append(source)
        return filtered_sources
    
    def filter_sentence(self,sentence):
        sentence = self.filter_sensitive_words(sentence)
        sentence = self.rebranding_words(sentence)
        return sentence


def token_to_sentence_gen(answer:Iterable[str],stop_signals: Union[list[str],set[str]]):
    accumulated_chunk_ans = ""
    for ans in answer:
        accumulated_chunk_ans += ans
        if not (len(ans) > 0 and ans[-1] in stop_signals):
            continue
        yield accumulated_chunk_ans
        accumulated_chunk_ans = ""

    if accumulated_chunk_ans:
        yield accumulated_chunk_ans


def token_to_sentence_gen_market(answer:Iterable[str]):
    stop_signals = {',', '.', '?', '!', '，', '。', '！', '？'}
    return token_to_sentence_gen(answer,stop_signals)
