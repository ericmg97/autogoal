from transformers import BertModel, BertTokenizer
import torch
import numpy as np

from autogoal.kb import Sentence, MatrixContinuousDense, Tensor3, List
from autogoal.grammar import Discrete
from autogoal.utils import CacheManager, nice_repr


@nice_repr
class BertEmbedding:
    """
    Transforms a sentence into a list of vector embeddings using a Bert pretrained English model.

    ##### Notes

    On the first use the model `bert-case-uncased` from [huggingface/transformers](https://github.com/huggingface/transformers)
    will be downloaded. This may take a few minutes.

    If you are using the development container the model should be already downloaded for you.
    """

    def __init__(self):  # , length: Discrete(16, 512)):
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )
        print("Using device: %s" % self.device)
        self.model = None
        self.tokenizer = None

    def run(self, input: List(Sentence(language="english"))) -> Tensor3():
        if self.model is None:
            self.model = CacheManager.instance().get(
                "bert-model",
                lambda: BertModel.from_pretrained("bert-base-uncased").to(self.device),
            )
            self.tokenizer = CacheManager.instance().get(
                "bert-tokenizer",
                lambda: BertTokenizer.from_pretrained("bert-base-uncased"),
            )

        print("Tokenizing...", end="", flush=True)
        tokens = [
            self.tokenizer.encode(x, max_length=32, pad_to_max_length=True)
            for x in input
        ]
        print("done")

        ids = torch.tensor(tokens).to(self.device)

        with torch.no_grad():
            print("Embedding...", end="", flush=True)
            output = self.model(ids)[0].numpy()
            print("done")

        return output