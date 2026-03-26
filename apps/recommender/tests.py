from django.test import SimpleTestCase

from .scoring import (
    WORKLOAD_GAME,
    WORKLOAD_OFFICE,
    WORKLOAD_PRODUCTIVITY,
    build_normalization_stats,
    score_build,
)


class ScoringTests(SimpleTestCase):
    def setUp(self):
        self.cpus = [
            {"single_score": 200, "multi_score": 700, "base_clock": 3.5, "boost_clock": 5.0, "core_count": 8, "thread_count": 16, "tdp": 65},
            {"single_score": 280, "multi_score": 1200, "base_clock": 4.0, "boost_clock": 5.6, "core_count": 16, "thread_count": 32, "tdp": 170},
        ]
        self.gpus = [
            {"gaming_score": 180, "compute_score": 160, "core_clock": 2000, "memory_clock": 18000, "vram_size": 8, "tdp": 160},
            {"gaming_score": 320, "compute_score": 340, "core_clock": 2600, "memory_clock": 24000, "vram_size": 24, "tdp": 320},
        ]
        self.rams = [
            {"capacity": 16, "frequency": 3200, "latency": 18},
            {"capacity": 64, "frequency": 6400, "latency": 32},
        ]
        self.storages = [
            {"capacity": 512, "cache_size": 128, "read_speed": 3500, "write_speed": 3000, "random_read_iops": 300000, "random_write_iops": 250000},
            {"capacity": 4000, "cache_size": 4096, "read_speed": 10000, "write_speed": 8500, "random_read_iops": 1000000, "random_write_iops": 900000},
        ]
        self.stats = build_normalization_stats(self.cpus, self.gpus, self.rams, self.storages)

    def test_score_build_in_valid_range(self):
        result = score_build(
            cpu=self.cpus[0],
            gpu=self.gpus[0],
            ram=self.rams[0],
            storage=self.storages[0],
            stats=self.stats,
            workload=WORKLOAD_GAME,
        )
        self.assertGreaterEqual(result["total_score"], 0.0)
        self.assertLessEqual(result["total_score"], 1.0)

    def test_support_multiple_workloads(self):
        for workload in (WORKLOAD_GAME, WORKLOAD_OFFICE, WORKLOAD_PRODUCTIVITY):
            result = score_build(
                cpu=self.cpus[1],
                gpu=self.gpus[1],
                ram=self.rams[1],
                storage=self.storages[1],
                stats=self.stats,
                workload=workload,
            )
            self.assertIn("cpu_score", result)
            self.assertIn("gpu_score", result)
            self.assertIn("ram_score", result)
            self.assertIn("storage_score", result)
            self.assertIn("total_score", result)
