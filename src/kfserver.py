from typing import Dict

import kfserving
import tensorflow as tf
import tornado.web
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest

from .nlp import Nlp


class KFServer(kfserving.KFModel):
    __vectorizer: TfidfVectorizer
    __selector: SelectKBest
    __model: tf.keras.models.Sequential

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name
        self.ready = False

    def load(self):
        v, s, m = Nlp.load_from_disk()

        self.__vectorizer = v
        self.__selector = s
        self.__model = m

        self.ready = True

    def predict(self, request: Dict) -> Dict:
        key = "text"
        if key not in request:
            raise tornado.web.HTTPError(
                status_code=400,
                reason="no '{}' key in request JSON".format(key))
        text = request[key]

        t = Nlp.transform(text, self.__vectorizer, self.__selector)
        result = self.__model.predict(t)

        return {"result": result[0][0].item()}
