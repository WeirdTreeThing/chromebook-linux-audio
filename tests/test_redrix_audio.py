import contextlib
import io
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import functions


PRIORITY = "60-chromebook-redrix-mic-priority.conf"
GAIN = "61-chromebook-redrix-mic-gain.conf"
CONFIG_SOURCE = Path(functions.__file__).resolve().parent / "conf" / "redrix"


class AudioVersionTests(unittest.TestCase):
    def test_linked_version_takes_precedence(self):
        result = subprocess.CompletedProcess([], 0,
            "wireplumber\nCompiled with libwireplumber 0.5.13\n"
            "Linked with libwireplumber 0.5.9\n", "")
        with patch("functions.subprocess.run", return_value=result) as run:
            self.assertEqual(functions.audio_stack_version("wireplumber"), (0, 5, 9))
        run.assert_called_once_with(["wireplumber", "--version"], check=True,
                                    capture_output=True, text=True, timeout=5)

    def test_compiled_version_fallback_and_package_suffix(self):
        result = subprocess.CompletedProcess([], 0, "", "Compiled with libpipewire 1.4.0-2\n")
        with patch("functions.subprocess.run", return_value=result):
            self.assertEqual(functions.audio_stack_version("pipewire"), (1, 4, 0))

    def test_unknown_linked_version_does_not_use_compiled_version(self):
        result = subprocess.CompletedProcess([], 0,
            "Compiled with libwireplumber 0.5.13\nLinked with libwireplumber unknown\n", "")
        with patch("functions.subprocess.run", return_value=result):
            self.assertIsNone(functions.audio_stack_version("wireplumber"))

    def test_missing_failed_timed_out_and_unrecognised_commands(self):
        outcomes = [FileNotFoundError(), subprocess.CalledProcessError(1, "wireplumber"),
                    subprocess.TimeoutExpired("wireplumber", 5),
                    subprocess.CompletedProcess([], 0, "unrecognised output", "")]
        for outcome in outcomes:
            with self.subTest(outcome=outcome):
                kwargs = ({"side_effect": outcome} if isinstance(outcome, Exception)
                          else {"return_value": outcome})
                with patch("functions.subprocess.run", **kwargs):
                    self.assertIsNone(functions.audio_stack_version("wireplumber"))


class RedrixInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.product = root / "product_name"
        self.product.write_text("Redrix\n")
        self.destination = root / "wireplumber" / "wireplumber.conf.d"
        for name, value in (("REDRIX_PRODUCT_NAME", self.product),
                            ("REDRIX_WP_CONFIG_DIR", self.destination)):
            patcher = patch.object(functions, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def install(self, wp=(0, 5, 13), pw=(1, 4, 0)):
        def version_command(argv, **kwargs):
            version = {"wireplumber": wp, "pipewire": pw}[argv[0]]
            if isinstance(version, Exception):
                raise version
            output = (f"Linked with lib{argv[0]} {'.'.join(map(str, version))}\n"
                      if version is not None else "unknown version\n")
            return subprocess.CompletedProcess(argv, 0, output, "")

        output = io.StringIO()
        with patch("functions.subprocess.run", side_effect=version_command), \
                contextlib.redirect_stdout(output):
            functions.install_redrix_audio_config()
        return output.getvalue()

    def installed_names(self):
        return {path.name for path in self.destination.glob("*.conf")}

    def test_non_redrix_does_not_probe_versions_or_write(self):
        for board in ("Brya", "redrix-extra", "another-board", ""):
            with self.subTest(board=board):
                self.product.write_text(board)
                with patch("functions.subprocess.run") as run:
                    functions.install_redrix_audio_config()
                run.assert_not_called()
                self.assertFalse(self.destination.exists())

    def test_missing_dmi_does_not_install(self):
        self.product.unlink()
        with patch("functions.subprocess.run") as run, contextlib.redirect_stdout(io.StringIO()):
            functions.install_redrix_audio_config()
        run.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_normalised_board_and_exact_minimum_versions(self):
        self.product.write_text("  ReDrIx\n")
        output = self.install()
        self.assertIn("avoid applying the gain twice", output)
        self.assertIn("start input volume at 100%", output)
        self.assertEqual(self.installed_names(), {PRIORITY, GAIN})
        for name in (PRIORITY, GAIN):
            self.assertEqual((self.destination / name).read_bytes(),
                             (CONFIG_SOURCE / name).read_bytes())

    def test_priority_and_gain_version_boundaries(self):
        cases = [
            ((0, 4, 17), (1, 4, 0), set()),
            ((0, 5, 0), (1, 4, 0), {PRIORITY}),
            ((0, 5, 12), (1, 4, 0), {PRIORITY}),
            ((0, 5, 13), (1, 3, 81), {PRIORITY}),
            ((0, 5, 13), (1, 4, 0), {PRIORITY, GAIN}),
            ((0, 5, 14), (1, 6, 2), {PRIORITY, GAIN}),
            (None, (1, 6, 2), set()),
            ((0, 5, 13), None, {PRIORITY}),
            (FileNotFoundError(), (1, 6, 2), set()),
            ((0, 5, 13), subprocess.TimeoutExpired("pipewire", 5), {PRIORITY}),
        ]
        for wp, pw, expected in cases:
            with self.subTest(wp=wp, pw=pw):
                output = self.install(wp, pw)
                self.assertEqual(self.installed_names(), expected)
                self.assertEqual("gain was not installed" in output, GAIN not in expected)

    def test_rerun_and_downgrade_preserve_unmanaged_files(self):
        self.install()
        originals = {name: (self.destination / name).read_bytes() for name in (PRIORITY, GAIN)}
        unmanaged = self.destination / "80-user-microphone.conf"
        unmanaged.write_text("# user configuration\n")
        self.install()
        for name, content in originals.items():
            self.assertEqual((self.destination / name).read_bytes(), content)
        self.install(wp=(0, 5, 12))
        self.assertEqual(self.installed_names(), {PRIORITY, unmanaged.name})
        self.install(wp=None)
        self.assertEqual(self.installed_names(), {unmanaged.name})
        self.assertEqual(unmanaged.read_text(), "# user configuration\n")

    def test_moving_system_to_another_board_removes_only_managed_files(self):
        self.install()
        unmanaged = self.destination / "80-user-microphone.conf"
        unmanaged.write_text("# user configuration\n")
        self.product.write_text("AnotherBoard\n")
        with patch("functions.subprocess.run") as run:
            functions.install_redrix_audio_config()
        run.assert_not_called()
        self.assertEqual(self.installed_names(), {unmanaged.name})
        self.assertEqual(unmanaged.read_text(), "# user configuration\n")

    def test_node_rules_match_only_redrix_mic1_shape(self):
        valid = [
            "alsa_input.pci-0000_00_1f.3-platform-adl_rt5682_def.HiFi__Mic1__source",
            "alsa_input.pci-0000_00_1c.0-platform-adl_rt5682.HiFi__Mic1__source",
        ]
        invalid = [
            valid[0].replace("Mic1", "Mic2"),
            valid[0].replace("Mic1", "Headset"),
            valid[0].replace("alsa_input", "alsa_output"),
            valid[0].replace("adl_rt5682", "cml_rt5682"),
            valid[0] + ".unrelated",
            "alsa_input.usb-microphone.HiFi__Mic1__source",
        ]
        for name in (PRIORITY, GAIN):
            config = (CONFIG_SOURCE / name).read_text()
            expression = re.search(r'node.name\s*=\s*"~([^"]+)"', config).group(1)
            for node_name in valid:
                self.assertIsNotNone(re.search(expression, node_name), (name, node_name))
            for node_name in invalid:
                self.assertIsNone(re.search(expression, node_name), (name, node_name))

        gain_config = (CONFIG_SOURCE / GAIN).read_text()
        board_expression = re.search(r'alsa.long_card_name\s*=\s*"~([^"]+)"', gain_config).group(1)
        self.assertIsNotNone(re.search(board_expression, "Google-Redrix-rev3"))
        self.assertIsNone(re.search(board_expression, "Google-AnotherBoard-rev3"))


if __name__ == "__main__":
    unittest.main()
