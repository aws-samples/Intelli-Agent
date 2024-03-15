import os
import re
import csv
from typing import Iterable,Union
abs_dir = os.path.dirname(__file__)


class ContentFilterBase:
    def filter_sentence(self,sentence:str):
        raise NotImplementedError


class MarketContentFilter(ContentFilterBase):
    def __init__(
            self,
            sensitive_words_path=os.path.join(abs_dir,'sensitive_word.csv'),
            aws_products_path=os.path.join(abs_dir,'aws_products.csv'),
            ) -> None:
        self.sensitive_words = self.create_sensitive_words(sensitive_words_path)
        self.aws_products = self.create_aws_products(aws_products_path)
        # Define a regular expression pattern to match Chinese characters
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]')

    def create_sensitive_words(self,sensitive_words_path):
        sensitive_words = set()
        with open(sensitive_words_path, mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                sensitive_words.add(row[0])
        return sensitive_words

    def create_aws_products(self,aws_products_path):
        aws_products = {}
        with open(aws_products_path, mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                aws_products[row[0]] = aws_products[row[1]]
        return aws_products

    def filter_sensitive_words(self,sentence):
        for sensitive_word in self.sensitive_words:
            length = len(sensitive_word)
            sentence = sentence.replace(sensitive_word, '*' * length)
        return sentence

    def contains_chinese_characters(self,text):
        # Search for the pattern in the text
        match = re.search(self.chinese_pattern, text)

        # Return True if a match is found, otherwise False
        return match is not None

    def rebranding_words(self,sentence:str):
        cn_rebranding_dict = {'AWS': '亚马逊云科技'}
        # Replace "AWS" by "Amazon" in product name
        for key, value in self.aws_products.items():
            sentence = sentence.replace(key, value)
        # Replace "AWS" by "亚马逊云科技" if detected Chinese characters within its right time window of length 10
        for key, value in cn_rebranding_dict.items():
            index = sentence.find(key)
            while index != -1:
                substring = sentence[index : index + 10]
                if self.contains_chinese_characters(substring):
                    sentence = sentence.replace(key, value, 1)
                index = sentence.find(key)
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
        if not (len(ans) > 0 and ans[-1] in stop_signals and len(accumulated_chunk_ans) > 50):
            continue
        yield accumulated_chunk_ans
        accumulated_chunk_ans = ""

    if accumulated_chunk_ans:
        yield accumulated_chunk_ans


def token_to_sentence_gen_market(answer:Iterable[str]):
    stop_signals = {'，', '。'}
    return token_to_sentence_gen(answer,stop_signals)
