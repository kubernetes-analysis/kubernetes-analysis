import json
import os
import pickle
from typing import Any, List, Tuple

import numpy as np
import tensorflow as tf
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer


class Nlp():
    DATA_DIR = "data"
    MODEL_FILE = os.path.join(DATA_DIR, "model.h5")
    VECTORIZER_FILE = os.path.join(DATA_DIR, "vectorizer.pickle")

    __train_texts: List[str]
    __train_labels: Any

    __test_texts: List[str]
    __test_labels: Any

    def __init__(self, train_texts: List[str], train_labels: List[int],
                 test_texts: List[str], test_labels: List[int]):
        self.__train_texts = train_texts
        self.__train_labels = np.array(train_labels)
        self.__test_texts = test_texts
        self.__test_labels = np.array(test_labels)

    @staticmethod
    def predict(text: str) -> float:
        # Load the vectorizer
        vectorizer = pickle.load(open(Nlp.VECTORIZER_FILE, "rb"))

        # Prepare the input data
        data = vectorizer.transform([text]).toarray()

        # Load the model and predict
        model = tf.keras.models.load_model(Nlp.MODEL_FILE)
        result = model.predict(data)

        return result[0][0].item()

    def train(self, tune: bool = False):
        if tune:
            self.__tune()
        else:
            self.__train()

    def __tune(self):
        num_layers = [1, 2, 3]
        num_units = [8, 16, 32, 64, 128]

        # Save parameter combination and results
        params = {
            "layers": [],
            "units": [],
            "accuracy": [],
        }

        # Iterate over all parameter combinations
        for layers in num_layers:
            for units in num_units:
                params["layers"].append(layers)
                params["units"].append(units)

                accuracy, _ = self.__train(layers=layers, units=units)
                logger.info("Accuracy: {}, Layers: {}, Units: {}", accuracy,
                            layers, units)
                params["accuracy"].append(accuracy)

        logger.info("Tuning results: {}", params)

    def __train(self,
                learning_rate: float = 1e-3,
                epochs: int = 1000,
                batch_size: int = 128,
                layers: int = 2,
                units: int = 64,
                dropout_rate: float = 0.2):

        # Verify that test labels are in the same range as training labels
        num_classes = self.__num_classes()
        logger.info("Number of classes: {}", num_classes)

        unexpected_labels = [
            v for v in self.__test_labels if v not in range(num_classes)
        ]
        if len(unexpected_labels) > 0:
            raise ValueError(
                "Unexpected label values found in the validation set:"
                " {unexpected_labels}. Please make sure that the "
                "labels in the validation set are in the same range "
                "as training labels.".format(
                    unexpected_labels=unexpected_labels))

        x_train, x_val = Nlp.__vectorize(self.__train_texts, self.__test_texts)

        # Create model instance.
        model = Nlp.__mlp_model(layers, units, dropout_rate, x_train.shape[1:],
                                num_classes)
        logger.info("Created model with {} layers and {} units", layers, units)

        # Compile model with learning parameters.
        if num_classes == 2:
            loss = "binary_crossentropy"
        else:
            loss = "sparse_categorical_crossentropy"

        logger.info("Compiling model")
        optimizer = tf.keras.optimizers.Adam(lr=learning_rate)
        model.compile(optimizer=optimizer, loss=loss, metrics=["acc"])

        # Create callback for early stopping on validation loss. If the loss
        # does not decrease in two consecutive tries, stop training
        callbacks = [
            tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=2)
        ]

        # Train and validate model
        logger.info("Starting training")
        x = model.fit(
            x_train,
            self.__train_labels,
            epochs=epochs,
            callbacks=callbacks,
            validation_data=(x_val, self.__test_labels),
            verbose=2,  # logs once per epoch
            batch_size=batch_size)

        # Print confusion matric
        predictions = model.predict_classes(x_val)
        cm = tf.math.confusion_matrix(predictions=predictions,
                                      labels=self.__test_labels).numpy()
        logger.info("Confusion matrix:\n{}", cm)

        cm_norm = np.around(cm.astype("float") / cm.sum(axis=1)[:, np.newaxis],
                            decimals=3)
        logger.info("Confusion matrix normalized:\n{}", cm_norm)

        # Save the model
        logger.info("Saving model to file {}", Nlp.MODEL_FILE)
        model.save(Nlp.MODEL_FILE)

        logger.info("Validation accuracy: {}, loss: {}",
                    x.history["val_acc"][-1], x.history["val_loss"][-1])

        return x.history["val_acc"][-1], x.history["val_loss"][-1]

    def __num_classes(self) -> int:
        num_classes = max(self.__train_labels) + 1
        missing_classes = [
            i for i in range(num_classes) if i not in self.__train_labels
        ]

        if len(missing_classes) > 0:
            raise ValueError("Missing samples with label value(s) "
                             "{}. Please make sure you have "
                             "at least one sample for every label value "
                             "in the range(0, {})".format(
                                 missing_classes, num_classes - 1))

        if num_classes <= 1:
            raise ValueError("Invalid number of labels: {}."
                             "Please make sure there are at least two classes "
                             "of samples".format(num_classes))

        return num_classes

    @staticmethod
    def __vectorize(train: List[str], test: List[str]) -> Tuple[Any, Any]:
        vectorizer = TfidfVectorizer(
            # Split text into word tokens.
            analyzer="word",

            # Replace on decoding error
            decode_error="replace",

            # Use 1-grams + 2-grams
            ngram_range=(1, 2),

            # Minimum document/corpus frequency below which a token will be
            # discarded
            min_df=1,  # maybe use 2

            # Remove accents and perform other character normalization
            strip_accents="unicode",
        )

        # Learn vocabulary from training texts and vectorize training texts
        x_train = vectorizer.fit_transform(train)

        logger.info("Vocabulary len: {}", len(vectorizer.get_feature_names()))
        with open(os.path.join(Nlp.DATA_DIR, "features.json"), "w") as f:
            json.dump(vectorizer.get_feature_names(), f)
            logger.info("Wrote features to file {}", f.name)

        # Vectorize validation texts
        x_val = vectorizer.transform(test)

        # Save the vectorizer
        pickle.dump(vectorizer, open(Nlp.VECTORIZER_FILE, "wb"))

        return x_train.toarray(), x_val.toarray()

    @staticmethod
    def __mlp_model(layers: int, units: int, dropout_rate: float,
                    input_shape: Tuple, num_classes: int) -> Any:

        units, activation = Nlp.__get_last_layer_units_and_activation(
            num_classes)

        model = tf.keras.models.Sequential()
        model.add(
            tf.keras.layers.Dropout(rate=dropout_rate,
                                    input_shape=input_shape))

        for _ in range(layers - 1):
            model.add(tf.keras.layers.Dense(units=units, activation="relu"))
            model.add(tf.keras.layers.Dropout(rate=dropout_rate))

        model.add(tf.keras.layers.Dense(units=units, activation=activation))

        return model

    @staticmethod
    def __get_last_layer_units_and_activation(
            num_classes: int) -> Tuple[int, str]:
        if num_classes == 2:
            activation = "sigmoid"
            units = 1
        else:
            activation = "softmax"
            units = num_classes

        logger.info("Using units: {}", units)
        logger.info("Using activation function: {}", activation)
        return units, activation
