import json
import nnvm.symbol as sym
import nnvm.graph as graph

def infer_shape(sym):
    g = graph.create(sym)
    g._set_json_attr("shape_attr_key", "shape")
    g = g.apply("InferShape")
    jgraph = json.loads(g.apply("SaveJSON").json_attr("json"))
    jnodes = jgraph["nodes"]
    jnode_row_ptr = jgraph["node_row_ptr"]
    sdict = {}
    vshape = g.json_attr("shape")
    for i, n in enumerate(jnodes):
        begin, end = jnode_row_ptr[i], jnode_row_ptr[i + 1]
        sdict[n["name"]] = vshape[begin:end]
    return sdict

# Level 1
def test_dense():
    x = sym.Variable("x", shape=(10, 20))
    y = sym.dense(x, units=30, name="fc")
    sdict = infer_shape(y)
    assert(sdict["fc"][0] == [10, 30])
    assert(sdict["fc_bias"][0] == [30])


def test_concatenate():
    x1 = sym.Variable("x", shape=(10, 20))
    x2 = sym.Variable("y", shape=(10, 30))
    z = sym.concatenate(x1, x2, name="concat")
    sdict = infer_shape(z)
    assert(sdict["concat"][0] == [10, 50])
    z = sym.concatenate(x1, x1, axis=0, name="concat")
    sdict = infer_shape(z)
    assert(sdict["concat"][0] == [20, 20])


def test_split():
    x1 = sym.Variable("x", shape=(10, 20))
    z = sym.split(x1, indices_or_sections=[11, 9], name="y")
    sdict = infer_shape(z)
    assert(sdict["y"][0] == [10, 11])
    assert(sdict["y"][1] == [10, 9])
    z = sym.split(x1, indices_or_sections=2, name="y")
    sdict = infer_shape(z)
    assert(sdict["y"][0] == [10, 10])
    assert(sdict["y"][1] == [10, 10])


def test_batchnorm():
    x = sym.Variable("x", shape=(10, 20))
    y = sym.batch_norm(1 / x, name="bn")
    sdict = infer_shape(y)
    assert(sdict["bn_gamma"][0] == [20])


def test_flatten():
    x = sym.Variable("x", shape=(10, 20, 10))
    y = sym.flatten(x) * 2
    y = sym.exp(y, name="y")
    sdict = infer_shape(y)
    assert(sdict["y"][0] == [10, 200])


# Level 2
def test_conv2d():
    def check(in_shape, out_shape, **kwargs):
        x = sym.Variable("x", shape=in_shape)
        y = sym.conv2d(x, name="y", **kwargs)
        sdict = infer_shape(y)
        assert(tuple(sdict["y"][0]) == tuple(out_shape))

    check((4, 10, 10, 12),
          (4, 12, 10, 12),
          channels=12,
          kernel_size=(3,3),
          padding=(1,1))
    check((4, 10, 12, 4),
          (4, 8, 8, 5),
          channels=5,
          kernel_size=(3, 5),
          layout="NHWC")
    check((4, 10, 12, 4),
          (4, 6, 8, 5),
          channels=5,
          dilation=(2, 2),
          kernel_size=(3, 3),
          layout="NHWC")
    check((4, 10, 12, 4),
          (4, 5, 6, 5),
          channels=5,
          strides=(2, 2),
          kernel_size=(3, 3),
          padding=(1, 1),
          layout="NHWC")


def test_conv2d_transpose():
    def check(in_shape, out_shape, **kwargs):
        x = sym.Variable("x", shape=in_shape)
        y = sym.conv2d_transpose(x, name="y", **kwargs)
        sdict = infer_shape(y)
        assert(tuple(sdict["y"][0]) == tuple(out_shape))

    check((4, 10, 10, 12),
          (4, 15, 10, 12),
          channels=15,
          kernel_size=(3,3),
          padding=(1,1))
    check((4, 10, 10, 12),
          (4, 15, 10, 14),
          channels=15,
          kernel_size=(3, 5),
          padding=(1, 1))
    check((4, 10, 10, 12),
          (4, 15, 11, 15),
          channels=15,
          kernel_size=(3, 5),
          padding=(1, 1),
          output_padding=(1, 1))
    check((4, 10, 10, 12),
          (4, 15, 15, 11),
          channels=11,
          kernel_size=(5, 5),
          output_padding=(1, 1),
          layout="NHWC")


def test_max_pool2d():
    def check(in_shape, out_shape, **kwargs):
        x = sym.Variable("x", shape=in_shape)
        y = sym.max_pool2d(x, name="y", **kwargs)
        sdict = infer_shape(y)
        assert(tuple(sdict["y"][0]) == tuple(out_shape))

    check((4, 10, 12, 12),
          (4, 10, 12, 12),
          pool_size=(3,3),
          padding=(1,1))
    check((4, 10, 12, 12),
          (4, 10, 6, 6),
          pool_size=(3, 3),
          padding=(1, 1),
          strides=(2, 2))
    check((4, 10, 12, 12),
          (4, 10, 7, 7),
          pool_size=(3, 3),
          padding=(1, 1),
          strides=(2, 2),
          ceil_mode=True)
    check((4, 12, 14, 10),
          (4, 6, 7, 10),
          pool_size=(3, 3),
          padding=(1, 1),
          strides=(2, 2),
          layout="NHWC")


def test_global_pool2d():
    def check(in_shape, out_shape, **kwargs):
        x = sym.Variable("x", shape=in_shape)
        y = sym.global_max_pool2d(x, name="y", **kwargs)
        sdict = infer_shape(y)
        assert(tuple(sdict["y"][0]) == tuple(out_shape))

    check((4, 10, 12, 12),
          (4, 10, 1, 1))
    check((4, 10, 12, 12),
          (4, 1, 1, 12),
          layout="NHWC")


# Level 3
def test_reshape():
    def check(in_shape, tshape, out_shape):
        x = sym.Variable("x", shape=in_shape)
        y = sym.reshape(x, shape=tshape, name="y")
        sdict = infer_shape(y)
        assert(tuple(sdict["y"][0]) == tuple(out_shape))

    check((4,), (2, 2), (2, 2))
    check((2, 3, 4), (4, 0, 2), (4, 3, 2))
    check((2, 3, 4), (2, 0, 0), (2, 3, 4))
    check((2, 3, 4), (6, 1, -1), (6, 1, 4))
    check((2, 3, 4), (3, -1, 8), (3, 1, 8))
    check((2, 3, 4), (-1,), (24,))
    check((2, 3, 4), (-2,), (2, 3, 4))
    check((2, 3, 4), (2, -2), (2, 3, 4))
    check((2, 3, 4), (-2, 1, 1), (2, 3, 4, 1, 1))
    check((2, 3, 4), (-3, 4), (6, 4))
    check((2, 3, 4, 5), (-3, -3), (6, 20))
    check((2, 3, 4), (0, -3), (2, 12))
    check((2, 3, 4), (-3, -2), (6, 4))
    check((2, 3, 4), (-4, 1, 2, -2), (1, 2, 3, 4))
    check((2, 3, 4), (2, -4, -1, 3, -2), (2, 1, 3, 4))

if __name__ == "__main__":
    test_dense()
    test_concatenate()
    test_split()
    test_batchnorm()
    test_flatten()
    test_conv2d()
    test_conv2d_transpose()
    test_max_pool2d()
    test_global_pool2d()
    test_reshape()
