#
# Copyright (c) 2021, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

import numpy as np
import pytest
import tensorflow as tf

import merlin.models.tf as ml
from merlin.io import Dataset
from merlin.models.tf.blocks.core.aggregation import ElementWiseMultiply
from merlin.models.tf.utils import testing_utils
from merlin.schema import Tags


def test_elementwisemultiply():
    emb1 = np.random.uniform(-1, 1, size=(5, 10))
    emb2 = np.random.uniform(-1, 1, size=(5, 10))
    x = ElementWiseMultiply()({"emb1": tf.constant(emb1), "emb2": tf.constant(emb2)})

    assert np.mean(np.isclose(x.numpy(), np.multiply(emb1, emb2))) == 1
    assert x.numpy().shape == (5, 10)


@pytest.mark.parametrize("output_ids", [True, False])
def test_two_tower_block(testing_data: Dataset, output_ids: bool):
    two_tower = ml.TwoTowerBlock(
        testing_data.schema, query_tower=ml.MLPBlock([64, 128]), output_ids=output_ids
    )
    outputs = two_tower(ml.sample_batch(testing_data, batch_size=100, include_targets=False))

    assert len(outputs) == 4 if output_ids else 2
    for key in ["item", "query"]:
        assert list(outputs[key].shape) == [100, 128]
        tf.debugging.assert_near(
            tf.reduce_mean(tf.reduce_sum(tf.square(outputs[key]), axis=-1)),
            1.0,
            message="The TwoTowerBlock outputs should be L2-normalized, as "
            "that is a good practice.",
        )

    if output_ids:
        assert "query_id" in outputs
        assert "item_id" in outputs


def test_two_tower_block_tower_save(testing_data: Dataset, tmp_path):
    two_tower = ml.TwoTowerBlock(testing_data.schema, query_tower=ml.MLPBlock([64, 128]))
    two_tower(ml.sample_batch(testing_data, batch_size=100, include_targets=False))

    query_tower = two_tower.query_block()
    query_tower.save(str(tmp_path / "query_tower"))
    query_tower_copy = tf.keras.models.load_model(str(tmp_path / "query_tower"))
    weights = zip(query_tower.get_weights(), query_tower_copy.get_weights())
    assert all([np.array_equal(w1, w2) for w1, w2 in weights])
    assert set(query_tower_copy.schema.column_names) == set(
        query_tower_copy._saved_model_inputs_spec.keys()
    )

    item_tower = two_tower.item_block()
    item_tower.save(str(tmp_path / "item_tower"))
    item_tower_copy = tf.keras.models.load_model(str(tmp_path / "item_tower"))
    weights = zip(item_tower.get_weights(), item_tower_copy.get_weights())
    assert all([np.array_equal(w1, w2) for w1, w2 in weights])
    assert set(item_tower_copy.schema.column_names) == set(
        item_tower_copy._saved_model_inputs_spec.keys()
    )


def test_two_tower_block_serialization(testing_data: Dataset):
    two_tower = ml.TwoTowerBlock(testing_data.schema, query_tower=ml.MLPBlock([64, 128]))
    copy_two_tower = testing_utils.assert_serialization(two_tower)

    outputs = copy_two_tower(ml.sample_batch(testing_data, batch_size=100, include_targets=False))

    assert len(outputs) == 2
    for key in ["item", "query"]:
        assert list(outputs[key].shape) == [100, 128]


# TODO: Fix this test
# def test_two_tower_block_saving(ecommerce_data: SyntheticData):
#     two_tower = ml.TwoTowerBlock(ecommerce_data.schema, query_tower=ml.MLPBlock([64, 128]))
#
#     model = two_tower.connect(
#         ml.ItemRetrievalTask(ecommerce_data.schema, target_name="click", metrics=[])
#     )
#
#     dataset = ecommerce_data.tf_dataloader(batch_size=50)
#     copy_two_tower = testing_utils.assert_model_is_retrainable(model, dataset)
#
#     outputs = copy_two_tower(ecommerce_data.tf_tensor_dict)
#     assert list(outputs.shape) == [100, 1]


def test_two_tower_block_no_item_features(testing_data: Dataset):
    with pytest.raises(ValueError) as excinfo:
        schema = testing_data.schema.remove_by_tag(Tags.ITEM)
        ml.TwoTowerBlock(schema, query_tower=ml.MLPBlock([64]))
        assert "The schema should contain features with the tag `item`" in str(excinfo.value)


def test_two_tower_block_no_user_features(testing_data: Dataset):
    with pytest.raises(ValueError) as excinfo:
        schema = testing_data.schema.remove_by_tag(Tags.USER)
        ml.TwoTowerBlock(schema, query_tower=ml.MLPBlock([64]))
        assert "The schema should contain features with the tag `user`" in str(excinfo.value)


def test_two_tower_block_no_schema():
    with pytest.raises(ValueError) as excinfo:
        ml.TwoTowerBlock(schema=None, query_tower=ml.MLPBlock([64]))
    assert "The schema is required by TwoTower" in str(excinfo.value)


def test_two_tower_block_no_bottom_block(testing_data: Dataset):
    with pytest.raises(ValueError) as excinfo:
        ml.TwoTowerBlock(schema=testing_data.schema, query_tower=None)
    assert "The query_tower is required by TwoTower" in str(excinfo.value)
