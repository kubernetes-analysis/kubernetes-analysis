import logging
from typing import Any, List, Tuple

import numpy as np
import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, f_classif


class Train():
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

    def run(self,
            learning_rate: float = 1e-3,
            epochs: int = 1000,
            batch_size: int = 128,
            layers: int = 2,
            units: int = 64,
            dropout_rate: float = 0.2):

        # Verify that test labels are in the same range as training labels
        num_classes = self.__num_classes()
        logging.info("Number of classes: %d", num_classes)

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

        x_train, x_val = self.__vectorize()

        # Create model instance.
        model = Train.__mlp_model(layers, units, dropout_rate,
                                  x_train.shape[1:], num_classes)
        logging.info("Created model with %d layers and %d units", layers,
                     units)

        # Compile model with learning parameters.
        if num_classes == 2:
            loss = "binary_crossentropy"
        else:
            loss = "sparse_categorical_crossentropy"

        optimizer = tf.keras.optimizers.Adam(lr=learning_rate)
        model.compile(optimizer=optimizer, loss=loss, metrics=["acc"])

        # Create callback for early stopping on validation loss. If the loss
        # does not decrease in two consecutive tries, stop training
        callbacks = [
            tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=2)
        ]

        # Train and validate model
        x = model.fit(
            x_train,
            self.__train_labels,
            epochs=epochs,
            callbacks=callbacks,
            validation_data=(x_val, self.__test_labels),
            verbose=2,  # logs once per epoch
            batch_size=batch_size)

        logging.info("Validation accuracy: %f, loss: %f",
                     x.history["val_acc"][-1], x.history["val_loss"][-1])

        # Save the model
        model.save("data/model.h5")
        return x.history["val_acc"][-1], x.history["val_loss"][-1]

    def __num_classes(self) -> int:
        num_classes = max(self.__train_labels) + 1
        missing_classes = [
            i for i in range(num_classes) if i not in self.__train_labels
        ]

        if len(missing_classes) > 0:
            raise ValueError("Missing samples with label value(s) "
                             "{missing_classes}. Please make sure you have "
                             "at least one sample for every label value "
                             "in the range(0, {max_class})".format(
                                 missing_classes=missing_classes,
                                 max_class=num_classes - 1))

        if num_classes <= 1:
            raise ValueError("Invalid number of labels: {num_classes}."
                             "Please make sure there are at least two classes "
                             "of samples".format(num_classes=num_classes))

        return num_classes

    def __vectorize(self) -> Tuple[Any, Any]:

        # Create keyword arguments to pass to the vectorizer
        kwargs = {
            "dtype": "int32",
            "strip_accents": "unicode",
            "decode_error": "replace",

            # Use 1-grams + 2-grams
            "ngram_range": (1, 2),

            # Split text into word tokens.
            "analyzer": "word",

            # Minimum document/corpus frequency below which a token will be
            # discarded
            "min_df": 2,
        }

        vectorizer = TfidfVectorizer(**kwargs)

        # Learn vocabulary from training texts and vectorize training texts
        x_train = vectorizer.fit_transform(self.__train_texts)

        # Vectorize validation texts
        x_val = vectorizer.transform(self.__test_texts)

        # Limit on the number of features. We use the top 20K features
        top = 20000

        # Select top "k" of the vectorized features
        selector = SelectKBest(f_classif, k=min(top, x_train.shape[1]))
        selector.fit(x_train, self.__train_labels)

        x_train = selector.transform(x_train).astype("float32")
        x_val = selector.transform(x_val).astype("float32")

        return x_train.toarray(), x_val.toarray()

    @staticmethod
    def __mlp_model(layers: int, units: int, dropout_rate: float,
                    input_shape: Tuple, num_classes: int) -> Any:

        units, activation = Train.__get_last_layer_units_and_activation(
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

        return units, activation
