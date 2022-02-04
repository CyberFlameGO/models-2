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


import tensorflow as tf
from tensorflow.keras.losses import BinaryCrossentropy
from tensorflow.keras.losses import MeanSquaredError as KerasMeanSquaredError

from .loss_base import LossRegistryMixin


@LossRegistryMixin.registry.register("mse")
@tf.keras.utils.register_keras_serializable(package="merlin_models")
class MeanSquaredError(KerasMeanSquaredError, LossRegistryMixin):
    """Extends `tf.keras.losses.MeanSquaredError` to adds support to
    the loss_registry, so that the loss can be defined by the user
    by a string alias name.
    """


@LossRegistryMixin.registry.register("binary_crossentropy")
@tf.keras.utils.register_keras_serializable(package="merlin_models")
class BinaryCrossEntropy(BinaryCrossentropy, LossRegistryMixin):
    """Extends `tf.keras.losses.BinaryCrossentropy` to add support to
    the loss_registry, so that the loss can be defined by the user
    by a string alias name.
    """

    def __init__(self, from_logits=True, **kwargs):
        super().__init__(from_logits=from_logits, **kwargs)
