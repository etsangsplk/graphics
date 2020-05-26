# Copyright 2020 The TensorFlow Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for lambertian reflectance."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import sys

from absl.testing import flagsaver
from absl.testing import parameterized
import numpy as np
import tensorflow as tf

from tensorflow_graphics.rendering.reflectance import lambertian
from tensorflow_graphics.util import test_case


class LambertianTest(test_case.TestCase):

  @flagsaver.flagsaver(tfg_add_asserts_to_graph=False)
  def test_brdf_jacobian_random(self):
    """Tests the Jacobian of brdf."""
    tensor_size = np.random.randint(3)
    tensor_shape = np.random.randint(1, 10, size=(tensor_size)).tolist()
    direction_incoming_light_init = np.random.uniform(
        1.0, 1.0, size=tensor_shape + [3])
    direction_outgoing_light_init = np.random.uniform(
        1.0, 1.0, size=tensor_shape + [3])
    surface_normal_init = np.random.uniform(1.0, 1.0, size=tensor_shape + [3])
    albedo_init = np.random.random(tensor_shape + [3])

    def lamertian_brdf_fn(albedo):
      return lambertian.brdf(direction_incoming_light_init,
                             direction_outgoing_light_init, surface_normal_init,
                             albedo)

    self.assert_jacobian_is_correct_fn(lamertian_brdf_fn, [albedo_init])

  @flagsaver.flagsaver(tfg_add_asserts_to_graph=False)
  def test_brdf_jacobian_preset(self):
    direction_incoming_light_init = np.array((0.0, 1.0, 0.0))
    direction_outgoing_light_init = np.array((0.0, 1.0, 0.0))
    surface_normal_init = np.array((1.0, 0.0, 0.0))
    albedo_init = np.array((1.0, 1.0, 1.0))

    def lamertian_brdf_fn(albedo):
      return lambertian.brdf(direction_incoming_light_init,
                             direction_outgoing_light_init, surface_normal_init,
                             albedo)

    self.assert_jacobian_is_correct_fn(lamertian_brdf_fn, [albedo_init])

  @parameterized.parameters(
      (-1.0, 1.0, 1.0 / math.pi),
      (1.0, 1.0, 0.0),
      (-1.0, -1.0, 0.0),
      (1.0, -1.0, 0.0),
  )
  def test_brdf_random(self, incoming_yz, outgoing_yz, ratio):
    tensor_size = np.random.randint(3)
    tensor_shape = np.random.randint(1, 10, size=(tensor_size)).tolist()
    albedo = np.random.uniform(low=0.0, high=1.0, size=tensor_shape + [3])
    direction_incoming_light = np.random.uniform(
        low=-1.0, high=1.0, size=tensor_shape + [3])
    direction_outgoing_light = np.random.uniform(
        low=-1.0, high=1.0, size=tensor_shape + [3])
    surface_normal = np.array((0.0, 1.0, 1.0))
    direction_incoming_light[..., 1:3] = incoming_yz
    direction_outgoing_light[..., 1:3] = outgoing_yz
    direction_incoming_light = direction_incoming_light / np.linalg.norm(
        direction_incoming_light, axis=-1, keepdims=True)
    direction_outgoing_light = direction_outgoing_light / np.linalg.norm(
        direction_outgoing_light, axis=-1, keepdims=True)
    surface_normal = surface_normal / np.linalg.norm(
        surface_normal, axis=-1, keepdims=True)

    gt = albedo * ratio
    pred = lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                           surface_normal, albedo)

    self.assertAllClose(gt, pred)

  def test_brdf_exceptions_raised(self):
    """Tests that the exceptions are raised correctly."""
    direction_incoming_light = np.random.uniform(-1.0, 1.0, size=(3,))
    direction_outgoing_light = np.random.uniform(-1.0, 1.0, size=(3,))
    surface_normal = np.random.uniform(-1.0, 1.0, size=(3,))
    albedo = np.random.uniform(0.0, 1.0, (3,))

    with self.subTest(name="assert_on_direction_incoming_light_not_normalized"):
      with self.assertRaises(tf.errors.InvalidArgumentError):
        self.evaluate(
            lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                            surface_normal, albedo))

    direction_incoming_light /= np.linalg.norm(
        direction_incoming_light, axis=-1)
    with self.subTest(name="assert_on_direction_outgoing_light_not_normalized"):
      with self.assertRaises(tf.errors.InvalidArgumentError):
        self.evaluate(
            lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                            surface_normal, albedo))

    direction_outgoing_light /= np.linalg.norm(
        direction_outgoing_light, axis=-1)
    with self.subTest(name="assert_on_surface_normal_not_normalized"):
      with self.assertRaises(tf.errors.InvalidArgumentError):
        self.evaluate(
            lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                            surface_normal, albedo))

    surface_normal /= np.linalg.norm(surface_normal, axis=-1)
    with self.subTest(name="assert_on_albedo_not_normalized"):
      albedo = np.random.uniform(-10.0, -sys.float_info.epsilon, (3,))

      with self.assertRaises(tf.errors.InvalidArgumentError):
        self.evaluate(
            lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                            surface_normal, albedo))

      albedo = np.random.uniform(sys.float_info.epsilon, 10.0, (3,))
      with self.assertRaises(tf.errors.InvalidArgumentError):
        self.evaluate(
            lambertian.brdf(direction_incoming_light, direction_outgoing_light,
                            surface_normal, albedo))

  @parameterized.parameters(
      ((3,), (3,), (3,), (3,)),
      ((None, 3), (None, 3), (None, 3), (None, 3)),
      ((1, 3), (1, 3), (1, 3), (1, 3)),
      ((2, 3), (2, 3), (2, 3), (2, 3)),
      ((3,), (1, 3), (1, 2, 3), (1, 3)),
      ((3,), (1, 3), (1, 2, 3), (1, 2, 2, 3)),
      ((1, 2, 2, 3), (1, 2, 3), (1, 3), (3,)),
  )
  def test_brdf_shape_exception_not_raised(self, *shape):
    """Tests that the shape exceptions are not raised."""
    self.assert_exception_is_not_raised(lambertian.brdf, shape)

  @parameterized.parameters(
      ("must have exactly 3 dimensions in axis -1", (1,), (3,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (2,), (3,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (4,), (3,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (1,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (2,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (4,), (3,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (1,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (2,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (4,), (3,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (3,), (4,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (3,), (2,)),
      ("must have exactly 3 dimensions in axis -1", (3,), (3,), (3,), (1,)),
      ("Not all batch dimensions are broadcast-compatible.", (2, 3), (3, 3),
       (3,), (3,)),
  )
  def test_brdf_shape_exception_raised(self, error_msg, *shape):
    """Tests that the shape exception is raised."""
    self.assert_exception_is_raised(lambertian.brdf, error_msg, shape)


if __name__ == "__main__":
  test_case.main()
