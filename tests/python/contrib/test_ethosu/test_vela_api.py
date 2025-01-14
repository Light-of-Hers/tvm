# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import pytest

pytest.importorskip("ethosu.vela")
import numpy as np
from ethosu.vela import api as vapi
from unittest.mock import patch

import tvm
from tvm import tir
from tvm.script import ty
from tvm.relay.backend.contrib.ethosu import vela_api

ACCEL_TYPES = [
    vapi.NpuAccelerator.Ethos_U55_256,
    vapi.NpuAccelerator.Ethos_U55_128,
    vapi.NpuAccelerator.Ethos_U55_64,
    vapi.NpuAccelerator.Ethos_U55_32,
]


"""Test case 1"""


@tvm.script.tir
class Module1:
    def main(
        placeholder: ty.handle,
        placeholder_1: ty.handle,
        placeholder_2: ty.handle,
        ethosu_conv2d: ty.handle,
    ) -> None:
        # function attr dict
        tir.func_attr({"global_symbol": "main", "tir.noalias": True})
        placeholder_3 = tir.match_buffer(
            placeholder, [1, 8, 8, 3], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        placeholder_4 = tir.match_buffer(
            placeholder_1, [48], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        placeholder_5 = tir.match_buffer(
            placeholder_2, [16], dtype="int32", elem_offset=0, align=128, offset_factor=1
        )
        ethosu_conv2d_1 = tir.match_buffer(
            ethosu_conv2d, [1, 8, 8, 16], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        # body
        tir.evaluate(
            tir.call_extern(
                "ethosu_conv2d",
                "uint8",
                8,
                8,
                3,
                8,
                0,
                8,
                tir.load("uint8", placeholder_3.data, 0),
                0,
                0,
                0,
                tir.float32(0.5),
                10,
                "NHWC",
                24,
                3,
                1,
                "uint8",
                8,
                8,
                16,
                8,
                0,
                8,
                tir.load("uint8", ethosu_conv2d_1.data, 0),
                0,
                0,
                0,
                tir.float32(0.25),
                14,
                "NHWC",
                128,
                16,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                tir.load("uint8", placeholder_4.data, 0),
                0,
                12,
                tir.load("uint8", placeholder_5.data, 0),
                0,
                0,
                0,
                0,
                0,
                "CLIP",
                0,
                0,
                "NONE",
                dtype="uint8",
            )
        )

    __tvm_meta__ = None


"""Test case 2 with per-channel quantization"""


@tvm.script.tir
class Module2:
    def main(
        placeholder: ty.handle,
        placeholder_1: ty.handle,
        placeholder_2: ty.handle,
        placeholder_6: ty.handle,
        ethosu_conv2d: ty.handle,
    ) -> None:
        # function attr dict
        tir.func_attr({"global_symbol": "main", "tir.noalias": True})
        placeholder_3 = tir.match_buffer(
            placeholder, [1, 8, 8, 3], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        placeholder_4 = tir.match_buffer(
            placeholder_1, [16, 1, 1, 3], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        placeholder_5 = tir.match_buffer(
            placeholder_2, [16], dtype="int32", elem_offset=0, align=128, offset_factor=1
        )
        # Per-channel weight scales
        placeholder_7 = tir.match_buffer(
            placeholder_6, [16], dtype="float32", elem_offset=0, align=128, offset_factor=1
        )
        ethosu_conv2d_1 = tir.match_buffer(
            ethosu_conv2d, [1, 8, 8, 16], dtype="uint8", elem_offset=0, align=128, offset_factor=1
        )
        # body
        tir.evaluate(
            tir.call_extern(
                "ethosu_conv2d",
                "uint8",
                8,
                8,
                3,
                8,
                0,
                8,
                tir.load("uint8", placeholder_3.data, 0),
                0,
                0,
                0,
                tir.float32(0.5),
                10,
                "NHWC",
                24,
                3,
                1,
                "uint8",
                8,
                8,
                16,
                8,
                0,
                8,
                tir.load("uint8", ethosu_conv2d_1.data, 0),
                0,
                0,
                0,
                tir.float32(0.25),
                14,
                "NHWC",
                128,
                16,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                tir.load("uint8", placeholder_4.data, 0),
                0,
                12,
                tir.load("uint8", placeholder_5.data, 0),
                0,
                0,
                0,
                0,
                0,
                "CLIP",
                0,
                0,
                "NONE",
                dtype="uint8",
            )
        )

    __tvm_meta__ = None


def test_get_optimal_block_config():
    block_configs_cases = [
        {
            "test": [
                vapi.NpuShape3D(10, 20, 8),
                vapi.NpuShape3D(10, 30, 16),
                vapi.NpuShape3D(10, 40, 32),
            ],
            "ref": vapi.NpuShape3D(10, 40, 32),
        },
        {
            "test": [
                vapi.NpuShape3D(10, 20, 8),
                vapi.NpuShape3D(10, 50, 32),
                vapi.NpuShape3D(10, 40, 32),
            ],
            "ref": vapi.NpuShape3D(10, 50, 32),
        },
        {
            "test": [
                vapi.NpuShape3D(50, 50, 8),
                vapi.NpuShape3D(10, 30, 32),
                vapi.NpuShape3D(8, 8, 64),
            ],
            "ref": vapi.NpuShape3D(8, 8, 64),
        },
    ]

    for test_case in block_configs_cases:
        assert vela_api._get_optimal_block_config(test_case["test"]) == test_case["ref"]


def test_compress_weights():
    test_vecs = [
        {
            # Stimulus
            "accel": vapi.NpuAccelerator.Ethos_U55_256,
            "block_depth": 8,
            "ifm_dtype": np.uint8,
            "shape": (3, 3, 16, 64),
            "layout": "HWIO",
            "zero_point": np.int64(134),
            "dilation": (1, 1),
            "is_depthwise": False,
            # Reference outputs
            "block_traversal": vapi.NpuBlockTraversal.PART_KERNEL_FIRST,
        },
        {
            # Stimulus
            "accel": vapi.NpuAccelerator.Ethos_U55_256,
            "block_depth": 8,
            "ifm_dtype": np.uint8,
            "shape": (3, 3, 32, 64),
            "layout": "HWIO",
            "zero_point": np.int64(134),
            "dilation": (1, 1),
            "is_depthwise": False,
            # Reference outputs
            "block_traversal": vapi.NpuBlockTraversal.DEPTH_FIRST,
        },
        {
            # Stimulus
            "accel": vapi.NpuAccelerator.Ethos_U55_256,
            "block_depth": 8,
            "ifm_dtype": np.int16,
            "shape": (3, 3, 16, 64),
            "layout": "HWIO",
            "zero_point": np.int64(134),
            "dilation": (1, 1),
            "is_depthwise": False,
            # Reference outputs
            "block_traversal": vapi.NpuBlockTraversal.DEPTH_FIRST,
        },
        # Pass-through value check
        {
            # Stimulus
            "accel": vapi.NpuAccelerator.Ethos_U55_128,
            "block_depth": 16,
            "ifm_dtype": np.uint8,
            "shape": (243, 152, 7, 1),
            "layout": "HWOI",
            "zero_point": np.int64(110),
            "dilation": (2, 2),
            "is_depthwise": True,
            # Reference outputs
            "block_traversal": vapi.NpuBlockTraversal.DEPTH_FIRST,
        },
        {
            # Stimulus
            "accel": vapi.NpuAccelerator.Ethos_U55_128,
            "block_depth": 32,
            "ifm_dtype": np.uint8,
            "shape": (64, 67, 35, 8),
            "layout": "OHWI",
            "zero_point": np.int64(100),
            "dilation": (1, 2),
            "is_depthwise": False,
            # Reference outputs
            "block_traversal": vapi.NpuBlockTraversal.PART_KERNEL_FIRST,
        },
    ]

    def verify(test_vec, mock_obj):
        layout_transform_indices = {
            "HWIO": (3, 0, 1, 2),
            "HWOI": (2, 0, 1, 3),
            "OHWI": (0, 1, 2, 3),
        }

        assert mock_obj
        mock_obj.assert_called_once()
        assert mock_obj.call_args[1]["accelerator"] == test_vec["accel"]
        assert mock_obj.call_args[1]["accelerator"] == test_vec["accel"]
        ishape = test_vec["shape"]
        shape_owhi = (
            ishape[layout_transform_indices[test_vec["layout"]][0]],
            ishape[layout_transform_indices[test_vec["layout"]][1]],
            ishape[layout_transform_indices[test_vec["layout"]][2]],
            ishape[layout_transform_indices[test_vec["layout"]][3]],
        )
        assert mock_obj.call_args[1]["weights_volume"].shape == shape_owhi
        assert mock_obj.call_args[1]["dilation_xy"] == test_vec["dilation"]
        assert mock_obj.call_args[1]["ifm_bitdepth"] == np.iinfo(test_vec["ifm_dtype"]).bits
        assert mock_obj.call_args[1]["ofm_block_depth"] == test_vec["block_depth"]
        assert mock_obj.call_args[1]["is_depthwise"] == test_vec["is_depthwise"]
        assert mock_obj.call_args[1]["block_traversal"] == test_vec["block_traversal"]

    def create_mock(test_vec):
        with patch(
            "tvm.relay.backend.contrib.ethosu.vela_api.vapi.npu_encode_weights"
        ) as mock_npu_encode_weights:
            ifm_bitdepth = np.iinfo(test_vec["ifm_dtype"]).bits
            ifm_dtype = test_vec["ifm_dtype"]
            max = np.iinfo(ifm_dtype).max
            min = np.iinfo(ifm_dtype).min
            values = np.random.randint(min, max, test_vec["shape"], ifm_dtype)
            compressed_weights = vela_api.compress_weights(
                weights=values,
                weights_zp=test_vec["zero_point"],
                weights_layout=test_vec["layout"],
                ifm_bitdepth=ifm_bitdepth,
                block_depth=test_vec["block_depth"],
                dilation=test_vec["dilation"],
                accel_type=test_vec["accel"],
                is_depthwise=test_vec["is_depthwise"],
            )
            return mock_npu_encode_weights
        return None

    for tv in test_vecs:
        mock_obj = create_mock(tv)
        verify(tv, mock_obj)


def test_pack_biases():
    test_vecs = [
        {
            # Stimulus
            "bias_length": 3,
            "ifm_scale": np.single(1.11111111),
            "ifm_dtype": np.uint8,
            "weight_scales": np.array(
                [np.single(0.91111111), np.single(1.01111111), np.single(1.11111111)]
            ),
            "ofm_scale": np.single(1.2),
            "is_activation_tanh_or_sigmoid": False,
            # Reference outputs
            "hw_scales": (1811663288, 2010504240, 1104672703),
            "hw_shifts": (31, 31, 30),
        },
        {
            # Stimulus
            "bias_length": 3,
            "ifm_scale": np.single(1.11111111),
            "ifm_dtype": np.int8,
            "weight_scales": np.array(
                [np.single(0.91111111), np.single(1.01111111), np.single(1.11111111)]
            ),
            "ofm_scale": np.single(1.2),
            "is_activation_tanh_or_sigmoid": False,
            # Reference outputs
            "hw_scales": (1811663185, 2010504312, 1104672720),
            "hw_shifts": (31, 31, 30),
        },
        {
            # Stimulus
            "bias_length": 3,
            "ifm_scale": np.single(1.11111111),
            "ifm_dtype": np.int16,
            "weight_scales": np.array(
                [np.single(0.91111111), np.single(1.01111111), np.single(1.11111111)]
            ),
            "ofm_scale": np.single(1.2),
            "is_activation_tanh_or_sigmoid": False,
            # Reference outputs
            "hw_scales": (27644, 30678, 16856),
            "hw_shifts": (15, 15, 14),
        },
    ]

    def verify(test_vec, mock_obj, packed_biases):
        assert mock_obj
        for idx, val in enumerate(test_vec["bias_values"]):
            assert val == mock_obj.call_args_list[idx][0][0]
            assert test_vec["hw_scales"][idx] == mock_obj.call_args_list[idx][0][1]
            assert test_vec["hw_shifts"][idx] == mock_obj.call_args_list[idx][0][2]

    def create_mock(test_vec):
        with patch(
            "tvm.relay.backend.contrib.ethosu.vela_api.vapi.npu_encode_bias"
        ) as mock_npu_encode_bias:
            mock_npu_encode_bias.return_value = bytearray(10)
            ifm_dtype = test_vec["ifm_dtype"]
            max = np.iinfo(ifm_dtype).max
            min = np.iinfo(ifm_dtype).min
            # tvm will always create biases in int32
            biases = np.random.randint(min, max, test_vec["bias_length"], np.int32)
            packed_biases = vela_api.pack_biases(
                biases=biases,
                ifm_scale=test_vec["ifm_scale"],
                ifm_dtype=test_vec["ifm_dtype"],
                weight_scales=test_vec["weight_scales"],
                ofm_scale=test_vec["ofm_scale"],
                is_activation_tanh_or_sigmoid=test_vec["is_activation_tanh_or_sigmoid"],
            )
            test_vec["bias_values"] = biases
            return mock_npu_encode_bias, packed_biases
        return None

    for _test_vec in test_vecs:
        mock_obj, packed_biases = create_mock(_test_vec)
        verify(_test_vec, mock_obj, packed_biases)


if __name__ == "__main__":
    pytest.main([__file__])
