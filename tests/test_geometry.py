from __future__ import annotations

import math
import unittest

from rsh.constants import KAPPA_MAX
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
            self.assertGreater(row.tau, 0.0)
            self.assertLess(row.tau, 1.0)
            self.assertAlmostEqual(norm(row.tangent), 1.0, places=12)
            self.assertAlmostEqual(norm(row.normal), 1.0, places=12)
            self.assertAlmostEqual(norm(row.binormal), 1.0, places=12)
            self.assertAlmostEqual(dot(row.tangent, row.normal), 0.0, places=12)
            self.assertAlmostEqual(dot(row.tangent, row.binormal), 0.0, places=12)
            self.assertAlmostEqual(dot(row.normal, row.binormal), 0.0, places=12)

    def test_even_sample_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "samples must be odd"):
            ModelConfig(samples=128).validate()

    def test_invalid_custom_schedule_is_rejected(self) -> None:
        from rsh.geometry import integrate_path

        with self.assertRaisesRegex(ValueError, "curvature schedule violates"):
            integrate_path(
                ModelConfig(samples=33),
                kappa_fn=lambda _s: KAPPA_MAX * 2.0,
            )

    def test_logical_sampling_is_exact_and_bounded(self) -> None:
        indices = logical_sample_indices(1_048_576, 8)
        self.assertEqual(indices, tuple((i * 1_048_576) // 8 for i in range(8)))
        self.assertEqual(indices[0], 0)
        self.assertTrue(all(a < b for a, b in zip(indices, indices[1:])))
        self.assertLess(indices[-1], 1_048_576)

    def test_configuration_rejects_non_finite_interval(self) -> None:
        with self.assertRaises(ValueError):
            ModelConfig(s1=math.inf).validate()


if __name__ == "__main__":
    unittest.main()
