from autogoal.search import RandomSearch, PESearch
from autogoal.kb import (
    build_pipelines,
    CategoricalVector,
    List,
    Word,
    MatrixContinuous,
    Tuple,
    infer_type
)

from autogoal.contrib import find_classes
import numpy as np
import random
import statistics


class AutoClassifier:
    def __init__(
        self,
        input=None,
        *,
        random_state=None,
        search_algorithm=PESearch,
        search_kwargs={},
        search_iterations=100,
        include_filter=".*",
        exclude_filter=None,
        validation_split=0.2,
        errors="warn",
        cross_validation="median",
        cross_validation_steps=3,
        registry=None,
    ):
        self.input = input
        self.search_algorithm = search_algorithm
        self.search_kwargs = search_kwargs
        self.search_iterations = search_iterations
        self.include_filter = include_filter
        self.exclude_filter = exclude_filter
        self.validation_split = validation_split
        self.errors = errors
        self.cross_validation = cross_validation
        self.cross_validation_steps = cross_validation_steps
        self.registry = registry
        self.random_state = random_state

        if random_state:
            np.random.seed(random_state)

    def fit(self, X, y, **kwargs):
        registry = self.registry or find_classes(
            include=self.include_filter, exclude=self.exclude_filter
        )

        self.pipeline_builder_ = build_pipelines(
            input=Tuple(self._start_type(X), CategoricalVector()),
            output=CategoricalVector(),
            registry=registry,
        )

        search = self.search_algorithm(
            self.pipeline_builder_,
            self._make_fitness_fn(X, y),
            random_state=self.random_state,
            errors=self.errors,
            **self.search_kwargs,
        )

        self.best_pipeline_, self.best_score_ = search.run(
            self.search_iterations, **kwargs
        )

        self.best_pipeline_.send("train")
        self.best_pipeline_.run((X, y))
        self.best_pipeline_.send("eval")

    def score(self, X, y):
        y_pred = self.best_pipeline_.run((X, np.zeros_like(y)))
        return (y_pred == y).astype(float).mean()

    def _start_type(self, X):
        return self.input or infer_type(X)

    def _make_fitness_fn(self, X, y):
        if isinstance(X, list):
            X = np.asarray(X)

        y = np.asarray(y)

        def fitness_fn(pipeline):
            scores = []

            for _ in range(self.cross_validation_steps):
                indices = np.arange(0, X.shape[0])
                np.random.shuffle(indices)
                split_index = int(self.validation_split * len(indices))
                train_indices = indices[:split_index]
                test_indices = indices[split_index:]

                X_train, y_train, X_test, y_test = (
                    X[train_indices],
                    y[train_indices],
                    X[test_indices],
                    y[test_indices],
                )

                pipeline.send("train")
                pipeline.run((X_train, y_train))
                pipeline.send("eval")
                y_pred = pipeline.run((X_test, np.zeros_like(y_test)))
                scores.append((y_pred == y_test).astype(float).mean())

            return getattr(statistics, self.cross_validation)(scores)

        return fitness_fn

    def predict(self, X):
        return self.best_pipeline_.run((X, [None] * len(X)))

class AutoChunker:
    def __init__(
        self,
        input=None,
        *,
        search_algorithm=RandomSearch,
        search_kwargs={},
        search_iterations=100,
        include_filter=".*",
        exclude_filter=None,
        validation_split=0.2,
        errors="warn",
    ):
        self.input = input
        self.search_algorithm = search_algorithm
        self.search_kwargs = search_kwargs
        self.search_iterations = search_iterations
        self.include_filter = include_filter
        self.exclude_filter = exclude_filter
        self.validation_split = validation_split
        self.errors = errors

    def fit(self, X, y, **kwargs):
        self.pipeline_builder_ = build_pipelines(
            input=self._start_type(),
            output=List(List(List(Tuple(Tuple(Word(), Word()), Word())))), # output: Tagged Documents
            registry=find_classes(
                include=self.include_filter, exclude=self.exclude_filter
            ),
        )

        search = self.search_algorithm(
            self.pipeline_builder_,
            self._make_fitness_fn(X, y),
            errors=self.errors,
            **self.search_kwargs,
        )

        self.best_pipeline_, self.best_score_ = search.run(self.search_iterations, **kwargs)

        self.best_pipeline_.send("train")
        self.best_pipeline_.run((X, y))
        self.best_pipeline_.send("eval")

    def score(self, X, y):
        _, y_pred = self.best_pipeline_.run((X, np.zeros_like(y)))
        return (y_pred == y).astype(float).mean()

    def _start_type(self):
        return self.input

    def _make_fitness_fn(self, X, y):
        #TODO: Integrate fitness function for meddocan
        X = np.asarray(X)
        y = np.asarray(y)

        indices = np.arange(0, len(X))
        np.random.shuffle(indices)
        split_index = int(self.validation_split * len(indices))
        train_indices = indices[:split_index]
        test_indices = indices[split_index:]

        X_train, y_train, X_test, y_test = (
            X[train_indices],
            y[train_indices],
            X[test_indices],
            y[test_indices],
        )

        def fitness_fn(pipeline):
            pipeline.send("train")
            pipeline.run((X_train, y_train))
            pipeline.send("eval")
            _, y_pred = pipeline.run((X_test, np.zeros_like(y_test)))
            return (y_pred == y_test).astype(float).mean()

        return fitness_fn

    def predict(self, X):
        return self.best_pipeline_.run((X, [None] * len(X)))