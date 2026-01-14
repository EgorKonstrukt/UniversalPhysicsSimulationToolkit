import os
import taichi as ti
import numpy as np

from UPST.config import config

if config.app.use_f64:
    ti_f = ti.f64
    np_f = np.float64
else:
    ti_f = ti.f32
    np_f = np.float32

ti.init(
    arch=ti.gpu,
    cpu_max_num_threads=os.cpu_count(),
    default_ip=ti.i32,
    default_fp=ti_f,
    debug=False,
    enable_fallback=True,
    device_memory_GB=8.0
)

@ti.kernel
def _taichi_compute_fractal(
    arr: ti.types.ndarray(dtype=ti.u8, ndim=3),
    x_min: ti_f, x_max: ti_f,
    y_min: ti_f, y_max: ti_f,
    w: ti.i32, h: ti.i32,
    max_iter: ti.i32, esc_sq: ti_f,
    fractal_type: ti.i32,
    c_real: ti_f, c_imag: ti_f,
    palette_r: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_g: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_b: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_len: ti.i32
):
    dx = (x_max - x_min) / ti.cast(w, ti_f)
    dy = (y_max - y_min) / ti.cast(h, ti_f)
    for py, px in ti.ndrange(h, w):
        y = y_max - ti.cast(py, ti_f) * dy
        x = x_min + ti.cast(px, ti_f) * dx
        zx: ti_f = 0.0
        zy: ti_f = 0.0
        cx: ti_f = 0.0
        cy: ti_f = 0.0
        if fractal_type == 0:
            cx, cy = x, y
        else:
            cx, cy = c_real, c_imag
            zx, zy = x, y
        escaped = max_iter
        for i in range(max_iter):
            zx2 = zx * zx
            zy2 = zy * zy
            if zx2 + zy2 > esc_sq:
                escaped = i
                break
            tmp = zx
            zx = zx2 - zy2 + cx
            zy = ti.static(2.0) * tmp * zy + cy
        r: ti.u8 = 0
        g: ti.u8 = 0
        b: ti.u8 = 0
        if escaped != max_iter:
            idx = ti.min(ti.max(0, escaped % palette_len), palette_len - 1)
            r = palette_r[idx]
            g = palette_g[idx]
            b = palette_b[idx]
        arr[py, px, 0] = r
        arr[py, px, 1] = g
        arr[py, px, 2] = b