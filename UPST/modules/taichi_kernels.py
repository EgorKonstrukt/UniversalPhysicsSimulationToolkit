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

@ti.kernel
def _taichi_compute_fractal_deepzoom(
    arr: ti.types.ndarray(dtype=ti.u8, ndim=3),
    center_x: ti_f, center_y: ti_f,
    zoom: ti_f,
    w: ti.i32, h: ti.i32,
    max_iter: ti.i32, esc_radius: ti_f,
    fractal_type: ti.i32,
    c_real: ti_f, c_imag: ti_f,
    palette_r: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_g: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_b: ti.types.ndarray(dtype=ti.u8, ndim=1),
    palette_len: ti.i32,
    ref_orbit_x: ti.types.ndarray(dtype=ti_f, ndim=1),
    ref_orbit_y: ti.types.ndarray(dtype=ti_f, ndim=1),
    ref_cx: ti_f, ref_cy: ti_f
):
    half_w = ti.cast(w, ti_f) * 0.5
    half_h = ti.cast(h, ti_f) * 0.5
    scale = zoom / half_w
    esc_sq = esc_radius * esc_radius
    for py, px in ti.ndrange(h, w):
        dx = (ti.cast(px, ti_f) - half_w) * scale
        dy = (ti.cast(py, ti_f) - half_h) * scale
        x = center_x + dx
        y = center_y + dy

        # Perturbation deltas (always defined)
        zx_p: ti_f = 0.0
        zy_p: ti_f = 0.0
        cx_p: ti_f = 0.0
        cy_p: ti_f = 0.0

        if fractal_type == 0:  # Mandelbrot
            # c = (ref_cx + dx, ref_cy + dy), so δc = (dx, dy)
            cx_p = dx
            cy_p = dy
            # z0 = 0 ⇒ δz0 = 0
        else:  # Julia
            # c fixed ⇒ δc = 0; z0 = (x, y) = (ref_cx + dx, ref_cy + dy)
            zx_p = dx
            zy_p = dy
            # δc = 0

        escaped = max_iter
        for i in range(max_iter):
            Zx = ref_orbit_x[i]
            Zy = ref_orbit_y[i]

            # Compute δz_{n+1} = 2*Z_n*δz_n + δz_n^2 + δc
            zx2_p = zx_p * zx_p
            zy2_p = zy_p * zy_p
            # 2*Z*δz = 2*(Zx*zx_p - Zy*zy_p, Zx*zy_p + Zy*zx_p)
            two_Z_dx = 2.0 * (Zx * zx_p - Zy * zy_p)
            two_Z_dy = 2.0 * (Zx * zy_p + Zy * zx_p)

            # Update δz
            new_zx_p = two_Z_dx + zx2_p - zy2_p + cx_p
            new_zy_p = two_Z_dy + 2.0 * zx_p * zy_p + cy_p
            zx_p, zy_p = new_zx_p, new_zy_p

            # Escape condition: |z| = |Z + δz| > esc_radius
            # Use safe bound: if |δz| > 2*|Z| + 2, then |z| > |Z| - |δz| > esc_radius (conservative)
            # But better: compute |z|² directly if |Z| not too large
            # Since we're in deep zoom, |Z| may be huge → use perturbation norm only when |Z| < esc_radius*2
            if Zx*Zx + Zy*Zy < 4.0 * esc_sq:
                zx_full = Zx + zx_p
                zy_full = Zy + zy_p
                if zx_full*zx_full + zy_full*zy_full > esc_sq:
                    escaped = i
                    break
            else:
                # When |Z| is large, δz dominates error — use |δz| > esc_radius * 0.5 as heuristic
                if zx_p*zx_p + zy_p*zy_p > 0.25 * esc_sq:
                    escaped = i
                    break

        r: ti.u8 = 0
        g: ti.u8 = 0
        b: ti.u8 = 0
        if escaped != max_iter:
            idx = escaped % palette_len
            r = palette_r[idx]
            g = palette_g[idx]
            b = palette_b[idx]
        arr[py, px, 0] = r
        arr[py, px, 1] = g
        arr[py, px, 2] = b
def compute_reference_orbit(ref_cx, ref_cy, max_iter, esc_sq):
    zx = zy = 0.0
    orbit_x = np.empty(max_iter, dtype=np_f)
    orbit_y = np.empty(max_iter, dtype=np_f)
    for i in range(max_iter):
        orbit_x[i] = zx
        orbit_y[i] = zy
        zx2 = zx * zx
        zy2 = zy * zy
        if zx2 + zy2 > esc_sq:
            break
        tmp = zx
        zx = zx2 - zy2 + ref_cx
        zy = 2.0 * tmp * zy + ref_cy
    return orbit_x, orbit_y