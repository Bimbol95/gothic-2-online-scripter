import json
import unittest

import g2o_api


class G2OApiTests(unittest.TestCase):
    def test_expected_snapshots_are_available(self):
        self.assertEqual(
            [path.stem for path in g2o_api.api_files()],
            ["0.3.9", "0.3.8", "0.3.7", "0.3.6"],
        )

    def test_exact_function_lookup_preserves_side_and_declaration(self):
        matches = list(
            g2o_api.search_records(
                g2o_api.load_api("0.3.9"),
                "setPlayerWorld",
                exact=True,
                side=None,
            )
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["side"], "server")
        self.assertEqual(
            matches[0]["record"]["declaration"],
            "void setPlayerWorld(int id, string world, string startPointName)",
        )

    def test_class_method_lookup_includes_owner(self):
        matches = list(
            g2o_api.search_records(
                g2o_api.load_api("0.3.9"),
                "Camera.setPosition",
                exact=True,
                side="client",
            )
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["owner"], "Camera")

    def test_reference_hashes_match_manifest(self):
        manifest_path = g2o_api.API_DIR / "sources.json"
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(len(manifest["files"]), 6)
        self.assertEqual(g2o_api.command_verify(None), 0)


if __name__ == "__main__":
    unittest.main()
