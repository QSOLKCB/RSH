from __future__ import annotations

import math
import unittest

from rsh.constants import (
    KAPPA_MAX,
    TAU_MAX_EXCLUSIVE,
    TAU_MIN_EXCLUSIVE,
)
from rsh.geometry import (
    ModelConfig,
    build_path,
    dot,
    logical_sample_indices,
    norm,
)


class GeometryTests(unittest.TestCase):
    def test_default_path_satisfies_geometric_contracts(self) -> None:
        config = ModelConfig(samples=129)
        rows = build_path(config)

        self.assertEqual(len(rows), 129)
        centre = rows[len(rows) // 2]
        self.assertEqual(centre.p, 0.5)
        self.assertLessEqual(norm(centre.position), 1.0e-12)

        for row in rows:
            self.assertGreaterEqual(row.kappa, 0.0)
            self.assertLessEqual(row.kappa, KAPPA_MAX + 1.0e-12)
            self.assertGreater(row.tau, TAU_MIN_EXCLUSIVE)
            self.assertLess(row.tau, TAU_MAX_EXCLUSIVE)
            self.assertAlmostEqual(
                norm(row.tangent),
                1.0,
                places=12,
            )
            self.assertAlmostEqual(
                norm(row.normal),
                1.0,
                places=12,
            )
            self.assertAlmostEqual(
                norm(row.binormal),
                1.0,
                places=12,
            )
            self.assertAlmostEqual(
                dot(row.tangent, row.normal),
                0.0,
                places=12,
            )
            self.assertAlmostEqual(
                dot(row.tangent, row.binormal),
                0.0,
                places=12,
            )
            self.assertAlmostEqual(
                dot(row.normal, row.binormal),
                0.0,
                places=12,
            )

    def test_even_sample_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "samples must be odd",
        ):
            ModelConfig(samples=128).validate()

    def test_invalid_custom_schedule_is_rejected(self) -> None:
        from rsh.geometry import integrate_path

        with self.assertRaisesRegex(
            ValueError,
            "curvature schedule violates",
        ):
            integrate_path(
                ModelConfig(samples=33),
                kappa_fn=lambda _s: KAPPA_MAX * 2.0,
            )

    def test_norm_handles_large_finite_components(self) -> None:
        value = norm((1.0e154, 1.0e154, 0.0))
        self.assertTrue(math.isfinite(value))
        self.assertAlmostEqual(
            value / 1.0e154,
            math.sqrt(2.0),
            places=15,
        )

    def test_large_finite_interval_is_not_misreported_as_zero(self) -> None:
        rows = build_path(ModelConfig(samples=3, s1=1.0e155))
        self.assertTrue(
            all(math.isfinite(component) for component in rows[-1].position)
        )
        self.assertAlmostEqual(norm(rows[-1].tangent), 1.0, places=12)

    def test_logical_sampling_is_exact_and_bounded(self) -> None:
        indices = logical_sample_indices(1_048_576, 8)
        self.assertEqual(
            indices,
            tuple((i * 1_048_576) // 8 for i in range(8)),
        )
        self.assertEqual(indices[0], 0)
        self.assertTrue(
            all(a < b for a, b in zip(indices, indices[1:]))
        )
        self.assertLess(indices[-1], 1_048_576)

    def test_configuration_rejects_non_finite_interval(self) -> None:
        with self.assertRaises(ValueError):
            ModelConfig(s1=math.inf).validate()


if __name__ == "__main__":
    unittest.main()
