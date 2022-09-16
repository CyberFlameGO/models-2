import pytest
import tensorflow as tf
from transformers import BertConfig

import merlin.models.tf as mm
from merlin.io import Dataset
from merlin.models.tf.blocks.transformer import (
    AlbertBlock,
    BertBlock,
    GPT2Block,
    RobertaBlock,
    XLNetBlock,
)
from merlin.models.tf.dataset import BatchedDataset
from merlin.models.tf.utils import testing_utils


def test_transformer_encoder():
    NUM_ROWS = 100
    SEQ_LENGTH = 10
    EMBED_DIM = 128

    inputs = tf.random.uniform((NUM_ROWS, SEQ_LENGTH, EMBED_DIM))
    transformer_encod = mm.TransformerBlock(
        transformer=BertConfig(hidden_size=EMBED_DIM, num_attention_heads=16)
    )
    outputs = transformer_encod(inputs)

    assert list(outputs.shape) == [NUM_ROWS, SEQ_LENGTH, EMBED_DIM]


def test_transformer_encoder_with_pooling():
    NUM_ROWS = 100
    SEQ_LENGTH = 10
    EMBED_DIM = 128

    inputs = tf.random.uniform((NUM_ROWS, SEQ_LENGTH, EMBED_DIM))
    transformer_encod = mm.TransformerBlock(
        transformer=BertConfig(hidden_size=EMBED_DIM, num_attention_heads=16), post="pooler_output"
    )
    outputs = transformer_encod(inputs)

    assert list(outputs.shape) == [NUM_ROWS, EMBED_DIM]


@pytest.mark.parametrize("encoder", [XLNetBlock, BertBlock, AlbertBlock, RobertaBlock, GPT2Block])
def test_hf_tranformers_blocks(encoder):
    NUM_ROWS = 100
    SEQ_LENGTH = 10
    EMBED_DIM = 128
    inputs = tf.random.uniform((NUM_ROWS, SEQ_LENGTH, EMBED_DIM))
    transformer_encod = encoder.build_transformer_layer(
        d_model=EMBED_DIM, n_head=8, n_layer=2, max_seq_length=SEQ_LENGTH
    )
    outputs = transformer_encod(inputs)
    assert list(outputs.shape) == [NUM_ROWS, SEQ_LENGTH, EMBED_DIM]


@pytest.mark.parametrize("run_eagerly", [True, False])
def test_transformer_as_classfication_model(sequence_testing_data: Dataset, run_eagerly):
    EMBED_DIM = 48
    loader, schema = classification_loader(sequence_testing_data)

    model = mm.Model(
        mm.InputBlockV2(
            schema,
            embeddings=mm.Embeddings(schema, sequence_combiner=None),
        ),
        BertBlock.build_transformer_layer(
            d_model=EMBED_DIM,
            n_head=8,
            n_layer=2,
            max_seq_length=4,
            post="pooler_output",
        ),
        mm.CategoricalPrediction(
            prediction=schema["user_country"],
        ),
    )

    batch = next(iter(loader))[0]
    outputs = model(batch)
    assert list(outputs.shape) == [50, 63]
    testing_utils.model_test(model, loader, run_eagerly=run_eagerly)


def test_tranformer_with_prepare_module(sequence_testing_data):
    NUM_ROWS = 100
    SEQ_LENGTH = 10
    EMBED_DIM = 128
    inputs = tf.random.uniform((NUM_ROWS, SEQ_LENGTH, EMBED_DIM))

    from merlin.models.tf.blocks.transformer import TransformerPrepare

    class DummyPrepare(TransformerPrepare):
        def call(self, inputs, features=None):
            bs = tf.shape(inputs["inputs_embeds"])[0]
            seq_len = self.transformer.config.max_position_embeddings
            attention_mask = tf.ones((bs, seq_len - 1))
            inputs.update({"attention_mask": attention_mask})
            return inputs

    transformer_encod = BertBlock.build_transformer_layer(
        d_model=EMBED_DIM,
        n_head=8,
        n_layer=2,
        max_seq_length=SEQ_LENGTH,
        pre=DummyPrepare,
    )

    outputs = transformer_encod(inputs)
    assert list(outputs.shape) == [NUM_ROWS, SEQ_LENGTH, EMBED_DIM]


def classification_loader(sequence_testing_data: Dataset):
    def _target_to_onehot(inputs, targets):
        targets = tf.squeeze(tf.one_hot(targets, 63))
        return inputs, targets

    schema = sequence_testing_data.schema.select_by_name(
        ["item_id_seq", "categories", "user_country"]
    )
    schema["user_country"] = schema["user_country"].with_tags(
        schema["user_country"].tags + "target"
    )
    sequence_testing_data.schema = schema
    dataloader = BatchedDataset(sequence_testing_data, batch_size=50)
    dataloader = dataloader.map(_target_to_onehot)
    return dataloader, schema
