import re
import string
from typing import List

import nltk
from nltk import pos_tag
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer

nltk.download('stopwords', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('wordnet', quiet=True)


class BagOfWords():
    __words: List[str]

    def __init__(self, text=None, words=None):
        self.__words = words
        if text:
            self.__words = []
            self.__parse(text)

    @property
    def words(self) -> List[str]:
        return self.__words

    def __str__(self) -> str:
        return ", ".join(self.__words)

    def __parse(self, input_text: str):
        text = input_text.lower()

        # remove special characters
        text = re.sub(r'[^A-Za-z0-9 ]+', '', text)

        # tokenize markdown and remove puncutation
        words = [word.strip(string.punctuation) for word in text.split(" ")]

        # remove stop words
        stop = stopwords.words('english')
        words = [x for x in words if x not in stop]

        # remove empty tokens
        words = [t for t in words if len(t) > 0]

        # lemmatize
        words = [
            WordNetLemmatizer().lemmatize(t[0], BagOfWords.__wordnet_pos(t[1]))
            for t in pos_tag(words)
        ]

        # remove words with only one letter
        words = [t for t in words if len(t) > 1]

        # remove common words
        common_words = ['use']
        words = list(filter(lambda x: x not in common_words, words))

        self.__words = words

    @staticmethod
    def __wordnet_pos(tag: str) -> bool:
        if tag.startswith("J"):
            return wordnet.ADJ

        if tag.startswith("V"):
            return wordnet.VERB

        if tag.startswith("N"):
            return wordnet.NOUN

        if tag.startswith("R"):
            return wordnet.ADV

        return wordnet.NOUN
