"""steam-engine-session against a real FIFO, a host stand-in process and real files.

The host stand-in reads the session's commands from the channel FIFO and
answers with the host's event lines (korri-steam-host's own unit tests cover
the host). Nothing here reaches Steam, a display or the network.
"""
import json
import os
import re
import shutil
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE = Path(__file__).parent
STEAM = HERE.parent

HOST = r'''
import fcntl, json, os, sys, time
channel = sys.argv[1]
behavior = sys.argv[2]
events = os.path.join(channel, "events.jsonl")
def emit(**event):
    with open(events, "a") as out:
        out.write(json.dumps(event, separators=(",", ":")) + "\n")
if behavior == "mismatch":
    emit(event="engine_mismatch", expected="aa", found="bb")
    sys.exit(1)
if behavior == "host-failed":
    # The start wrapper's refusal (host-run.sh fail), then nothing.
    emit(event="launch_refused", reason="host_failed",
         message="Steam engine: the engine host could not start")
    sys.exit(1)
# The real host holds its host lock for its whole life.
lock = open(os.path.join(channel, "host.lock"), "a")
fcntl.flock(lock, fcntl.LOCK_EX)
if behavior == "crash":
    # Signed in, then gone without a word, as a crash in steamclient.so.
    emit(event="mode", mode="session")
    time.sleep(1)
    os._exit(139)
emit(event="logon_state", state=4, logged_on=True, connected=True, offline=False)
while True:
    with open(os.path.join(channel, "commands")) as fifo:
        for line in fifo:
            with open(os.path.join(channel, "received"), "a") as seen:
                seen.write(line)
            verb, word = line.split()
            if verb == "refused":
                emit(event="launch_refused", reason=word)
                continue
            appid = int(word)
            emit(event="command", command=verb, appid=appid, queued=False)
            if verb == "install" and behavior == "install-fails":
                emit(event="app_job_finished", appid=appid, kind="install",
                     result="install_refused", state=1, seconds=0)
            elif verb == "install":
                emit(event="app_job_started", appid=appid, kind="install")
                emit(event="app_progress", appid=appid, kind="install", state=1026)
                time.sleep(0.3)
                emit(event="app_job_finished", appid=appid, kind="install",
                     result="installed", state=4, seconds=1)
            elif verb == "launched" and behavior == "pending":
                emit(event="sync_started", appid=appid, kind="launch")
                emit(event="cloud_pending", appid=appid,
                     operations=[{"operation": "upload_pending", "machine": "Living room"}])
            elif verb in ("retry", "play-anyway"):
                emit(event="cloud_pending_answered", appid=appid, answer=verb)
                emit(event="sync_finished", appid=appid, kind="launch", result="downloaded", state=2, seconds=1)
            elif verb == "launched":
                emit(event="sync_started", appid=appid, kind="launch")
                result = "conflict" if behavior == "conflict" else "synchronized"
                emit(event="sync_finished", appid=appid, kind="launch", result=result, state=2, seconds=1)
            elif verb == "exited":
                sys.exit(0)
'''


def appinfo(apps):
    """An appinfo.vdf (format 0x07564429) with the given apps' key/values."""
    strings = []

    def key(name):
        if name not in strings:
            strings.append(name)
        return struct.pack("<I", strings.index(name))

    def obj(values):
        out = b""
        for name, value in values.items():
            if isinstance(value, dict):
                out += b"\x00" + key(name) + obj(value)
            else:
                out += b"\x01" + key(name) + value.encode() + b"\x00"
        return out + b"\x08"

    records = b""
    for appid, values in apps.items():
        body = bytes(4 + 4 + 8 + 20 + 4 + 20) + obj({"appinfo": values})
        records += struct.pack("<II", appid, len(body)) + body
    records += struct.pack("<I", 0)
    table = 16 + len(records)
    out = struct.pack("<IIq", 0x07564429, 1, table) + records
    out += struct.pack("<I", len(strings)) + b"".join(s.encode() + b"\x00" for s in strings)
    return out


def launch_config(*entries, depots=None):
    app = {"common": {"name": "Game", "type": "Game"},
           "config": {"installdir": "Game", "launch": {str(i): e for i, e in enumerate(entries)}}}
    if depots:
        app["depots"] = {str(d): {"config": {"oslist": os}} if os else {} for d, os in depots.items()}
    return app


# VVVVVV's shape: shared 70301, Windows 70302, Linux 70303; both launch entries.
BOTH = dict(
    entries=({"executable": "bin\\game.exe", "arguments": "-x", "config": {"oslist": "windows"}},
             {"executable": "game.sh", "config": {"oslist": "linux"}}),
    depots={70301: None, 70302: "windows", 70303: "linux"},
)


def manifest_text(depots=()):
    inner = "".join(f'\t\t"{d}"\n\t\t{{\n\t\t\t"manifest"\t\t"1"\n\t\t}}\n' for d in depots)
    return ('"AppState"\n{\n\t"appid"\t\t"401710"\n\t"installdir"\t\t"Game"\n'
            f'\t"InstalledDepots"\n\t{{\n{inner}\t}}\n}}\n')


class LaunchEntryTests(unittest.TestCase):
    def pick(self, app, os_name="windows"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "appinfo.vdf"
            path.write_bytes(appinfo({401710: app}))
            return subprocess.run(
                [sys.executable, str(HERE / "launch-entry.py"), str(path), "401710", "--os", os_name],
                capture_output=True, text=True, check=False,
            )

    def test_prefers_the_default_64_bit_windows_entry(self):
        result = self.pick(launch_config(
            {"executable": "game32.exe", "config": {"oslist": "windows", "osarch": "32"}},
            {"executable": "bin\\game.exe", "arguments": "-a \"b c\"", "config": {"oslist": "windows"}},
            {"executable": "game.sh", "config": {"oslist": "linux"}},
        ))
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if not line.startswith("ARGV"))
        self.assertEqual(shlex.split(fields["EXE"]), ["bin/game.exe"])
        self.assertIn("ARGV=(-a 'b c')", result.stdout)

    def test_platforms_follow_the_installed_depots(self):
        app = launch_config(*BOTH["entries"], depots=BOTH["depots"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "appinfo.vdf"
            path.write_bytes(appinfo({401710: app}))
            manifest = Path(tmp) / "appmanifest.acf"
            for depots, order in (((70301, 70303), "linux"), ((70301, 70302), "windows linux"),
                                  ((70301,), "windows linux"), ((), "windows linux")):
                manifest.write_text(manifest_text(depots))
                result = subprocess.run(
                    [sys.executable, str(HERE / "launch-entry.py"), str(path), "401710",
                     "--platforms", str(manifest)], capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.strip(), order, depots)

    def test_no_entry_for_the_os_fails(self):
        app = launch_config({"executable": "game.sh", "config": {"oslist": "linux"}})
        self.assertNotEqual(self.pick(app).returncode, 0)
        self.assertEqual(self.pick(app, "linux").returncode, 0)


# What packages/engine.nix puts on the session program's PATH: coreutils,
# gnugrep, gnused, jq, python3, util-linux (flock); systemd-notify is faked.
SESSION_TOOLS = ["cat", "dirname", "head", "ln", "mkdir", "seq", "sleep", "stat", "tail",
                 "timeout", "tr", "true", "grep", "sed", "jq", "python3", "flock"]


def vz(zip_bytes):
    """A Valve VZa package of zip_bytes (layout in legacycompat-unpack.py)."""
    import lzma
    import zlib
    filters = [{"id": lzma.FILTER_LZMA1, "dict_size": 1 << 20, "lc": 3, "lp": 0, "pb": 2}]
    stream = lzma.compress(zip_bytes, format=lzma.FORMAT_RAW, filters=filters)
    props = bytes([3 + 0 * 9 + 2 * 45]) + struct.pack("<I", 1 << 20)
    return (b"VZa" + struct.pack("<I", 0) + props + stream
            + struct.pack("<II", zlib.crc32(zip_bytes) & 0xFFFFFFFF, len(zip_bytes)) + b"zv")


def valve_zip(extra=(), links=None):
    """bins_misc's shape: real DLLs at the root, legacycompat links named with a backslash."""
    import io
    import zipfile
    out = io.BytesIO()
    links = {"steamclient.dll": "../steamclient.dll", "steamclient64.dll": "../steamclient64.dll",
             "GameOverlayRenderer64.dll": "../GameOverlayRenderer64.dll"} if links is None else links
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("legacycompat/", b"")
        for name in ("steamclient.dll", "steamclient64.dll", "GameOverlayRenderer64.dll",
                     "ubuntu12_64/disk-free"):
            archive.writestr(name, f"MZ {name}".encode())
        archive.writestr("legacycompat/Steam.dll", b"MZ Steam.dll")
        for name, target in links.items():
            info = zipfile.ZipInfo("legacycompat\\" + name)
            info.create_system = 3
            info.external_attr = (0o120755 << 16)
            archive.writestr(info, target.encode())
        for name, data in extra:
            archive.writestr(name, data)
    return out.getvalue()


class LegacycompatUnpackTests(unittest.TestCase):
    """steam-legacycompat-unpack on Valve-shaped packages (korri#589)."""

    def unpack(self, package):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "work").mkdir()
        (root / "package.zip.vz").write_bytes(package)
        result = subprocess.run([sys.executable, str(HERE / "legacycompat-unpack.py"), str(root / "work"),
                                 str(root / "package.zip.vz")], capture_output=True, text=True)
        return result, root / "work"

    def test_writes_valves_legacycompat_folder_with_its_links_as_files(self):
        result, work = self.unpack(vz(valve_zip()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(sorted(p.name for p in work.iterdir()), ["legacycompat"])
        folder = work / "legacycompat"
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["GameOverlayRenderer64.dll", "Steam.dll", "steamclient.dll", "steamclient64.dll"])
        for path in folder.iterdir():
            self.assertFalse(path.is_symlink(), path)
        self.assertEqual((folder / "steamclient64.dll").read_bytes(), b"MZ steamclient64.dll")
        self.assertEqual((folder / "Steam.dll").read_bytes(), b"MZ Steam.dll")

    def test_refuses_a_link_that_leads_anywhere_else(self):
        for target in ("/etc/passwd", "../../steamclient.dll", "../ubuntu12_64/disk-free", "../missing.dll"):
            with self.subTest(target=target):
                result, work = self.unpack(vz(valve_zip(links={"steamclient.dll": target,
                                                              "steamclient64.dll": "../steamclient64.dll"})))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse((work / "legacycompat").exists())

    def test_refuses_a_package_without_the_steamclient_dlls(self):
        result, _ = self.unpack(vz(valve_zip(links={})))
        self.assertEqual(result.returncode, 1)
        self.assertIn("steamclient.dll", result.stderr)

    def test_refuses_a_damaged_or_foreign_package(self):
        good = vz(valve_zip())
        for package in (good[:-20] + good[-10:], b"PK\x03\x04" + good[4:], good[:-6] + b"\xff\xff\xff\x7fzv"):
            result, work = self.unpack(package)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse((work / "legacycompat").exists())

    def test_writes_nothing_outside_the_folder_and_refuses_unsafe_names(self):
        # Entries deeper than legacycompat/<name> are not part of the folder.
        for name in ("legacycompat/../x.dll", "legacycompat/sub/x.dll", "x/legacycompat/y.dll"):
            with self.subTest(name=name):
                result, work = self.unpack(vz(valve_zip(extra=((name, b"x"),))))
                self.assertEqual(result.returncode, 0, result.stderr)
                written = sorted(str(p.relative_to(work)) for p in work.rglob("*"))
                self.assertEqual([p for p in written if "x.dll" in p or "y.dll" in p or "sub" in p], [])
        for name in ("legacycompat/.hidden", "legacycompat\\a:b.dll"):
            with self.subTest(name=name):
                result, work = self.unpack(vz(valve_zip(extra=((name, b"x"),))))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse((work / "legacycompat").exists())


class SessionScriptTests(unittest.TestCase):
    def test_the_session_program_never_runs_a_bare_sh(self):
        for script in ("session.sh", "host-run.sh"):
            for number, line in enumerate((HERE / script).read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertIsNone(re.search(r"(^|[\s;|&(`'\"])sh(\s|$)", code),
                                  f"{script}:{number}: {line.strip()}")


class HostWrapperTests(unittest.TestCase):
    """host-run.sh refuses a bad start with an event in the channel's log."""

    def run_wrapper(self, *args, home="/nonexistent/home"):
        return subprocess.run([shutil.which("bash"), str(HERE / "host-run.sh"), *args],
                              env={**os.environ, "HOME": home}, capture_output=True, text=True)

    def test_every_refusal_writes_one_host_failed_event_to_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "linuxarm64/steamclient.so"
            engine.parent.mkdir()
            engine.write_bytes(b"x")
            for args, home in (((), "/x/home"), (("/no/steamclient.so",), "/x/home"),
                               ((str(engine),), "/not-a-home")):
                result = self.run_wrapper(*args, home=home)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(json.loads(result.stdout), {
                    "event": "launch_refused", "reason": "host_failed",
                    "message": "Steam engine: the engine host could not start"})


    # Valve's names per platform, as packages/engine.nix substitutes them.
    ARM = {"engineFolder": "linuxarm64", "sdkLink": "sdkarm64", "otherEngineFolder": "", "otherSdkLink": ""}
    X86 = {"engineFolder": "linux64", "sdkLink": "sdk64", "otherEngineFolder": "linux32", "otherSdkLink": "sdk32"}

    def start_host(self, root, path=None, valve=None, other_library=True):
        """Run host-run.sh with stand-ins for the FHS, the host and the settings
        program, as korrid starts it for <root>/person/steam-engine."""
        valve = valve or self.ARM
        package = root / "cache/engine-package" / valve["engineFolder"] / "steamclient.so"
        package.parent.mkdir(parents=True)
        package.write_bytes(b"x")
        if valve["otherEngineFolder"] and other_library:
            other = package.parent.parent / valve["otherEngineFolder"] / "steamclient.so"
            other.parent.mkdir()
            other.write_bytes(b"y")
        # korrid's Proton, with the tool name @korri:proton's unpack writes.
        proton = root / "proton"
        proton.mkdir()
        (proton / "compatibilitytool.vdf").write_text(
            '"compatibilitytools"\n{\n  "compat_tools"\n  {\n    "proton-test-arm64"\n'
            '    {\n      "install_path" "."\n    }\n  }\n}\n')
        home = root / "person/steam-engine/home"
        home.mkdir(parents=True, exist_ok=True)
        fhs = root / "fhs/bin/korri-steam-engine-fhs"
        fhs.parent.mkdir(parents=True)
        fhs.write_text(f"#!{shutil.which('bash')}\nexec \"$@\"\n")
        fhs.chmod(0o755)
        seen = root / "seen.json"
        host = root / "host/bin/korri-steam-host"
        host.parent.mkdir(parents=True)
        host.write_text(
            f"#!{sys.executable}\nimport json, os, sys\n"
            f"open({str(seen)!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd(), "
            "'tools': os.environ.get('STEAM_EXTRA_COMPAT_TOOLS_PATHS'), "
            "'tool': os.environ.get('KORRI_STEAM_COMPAT_TOOL')}))\n")
        host.chmod(0o755)
        settings = root / "settings/bin/steam-vdf-settings"
        settings.parent.mkdir(parents=True)
        settings.write_text(f"#!{shutil.which('bash')}\nexit 0\n")
        settings.chmod(0o755)
        wrapper = root / "host-run.sh"
        text = (HERE / "host-run.sh").read_text()
        for name, value in (("fhs", fhs.parent.parent), ("host", host.parent.parent),
                            ("settings", settings.parent.parent),
                            *valve.items()):
            text = text.replace(f"@{name}@", str(value))
        wrapper.write_text(text)
        environment = {**os.environ, "HOME": str(home), "KORRI_PROTON_CACHYOS": str(proton)}
        if path is not None:
            environment["PATH"] = path
        result = subprocess.run(
            [shutil.which("bash"), str(wrapper), "--commands", str(root / "commands"), str(package)],
            env=environment, capture_output=True, text=True)
        return result, package, proton, seen

    def test_the_host_starts_with_the_folder_compat_tools_registered(self):
        # korri#531: the engine looks for compatibilitytools.d beside the real
        # path of steamclient.so (korrid's cache), so the wrapper names the
        # folder's own one in STEAM_EXTRA_COMPAT_TOOLS_PATHS.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, package, proton, seen = self.start_host(root)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            steam = root / "person/steam-engine/steam"
            self.assertEqual(json.loads(seen.read_text()), {
                "argv": ["--commands", str(root / "commands"), str(package)],
                "cwd": str(steam),
                "tools": str(steam / "compatibilitytools.d"),
                "tool": "proton-test-arm64",
            })
            # The folder's tool directory holds the link to korrid's Proton.
            self.assertEqual(os.readlink(steam / "compatibilitytools.d/proton-test-arm64"), str(proton))

    def test_the_folder_links_the_engine_under_valves_names_for_the_platform(self):
        for valve, links in (
            (self.ARM, {"steam/linuxarm64/steamclient.so": "linuxarm64/steamclient.so",
                        "home/.steam/sdkarm64": None}),
            (self.X86, {"steam/linux64/steamclient.so": "linux64/steamclient.so",
                        "steam/linux32/steamclient.so": "linux32/steamclient.so",
                        "home/.steam/sdk64": None, "home/.steam/sdk32": None}),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result, package, _, _ = self.start_host(root, valve=valve)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                engine = root / "person/steam-engine"
                cache = package.parent.parent
                for link, target in links.items():
                    # A library links to korrid's cache; an sdk link to the folder's own engine folder.
                    want = cache / target if target else engine / "steam" / {
                        "sdkarm64": "linuxarm64", "sdk64": "linux64", "sdk32": "linux32"}[Path(link).name]
                    self.assertEqual(os.readlink(engine / link), str(want), link)
                made = sorted(p.name for p in (engine / "home/.steam").iterdir())
                self.assertEqual(made, sorted(["steam", *(Path(l).name for l in links if l.startswith("home/"))]))

    def test_no_other_library_is_linked_when_the_package_has_none(self):
        # An x86_64 package without linux32 (not Valve's layout today) starts with the 64-bit links only.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, _, _, _ = self.start_host(root, valve=self.X86, other_library=False)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            engine = root / "person/steam-engine"
            self.assertFalse((engine / "steam/linux32").exists())
            self.assertFalse((engine / "home/.steam/sdk32").exists())

    def test_the_tool_name_comes_from_the_proton_folder(self):
        # Core ADR 0083: the wrapper fixes no Proton version.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, _, proton, seen = self.start_host(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            (proton / "compatibilitytool.vdf").write_text(
                '"compatibilitytools"\n{\n  "compat_tools"\n  {\n    "proton-other-9"\n    {\n    }\n  }\n}\n')
            wrapper = root / "host-run.sh"
            home = root / "person/steam-engine/home"
            package = root / "cache/engine-package/linuxarm64/steamclient.so"
            run = lambda: subprocess.run(
                [shutil.which("bash"), str(wrapper), "--commands", str(root / "commands"), str(package)],
                env={**os.environ, "HOME": str(home), "KORRI_PROTON_CACHYOS": str(proton)},
                capture_output=True, text=True)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(seen.read_text())["tool"], "proton-other-9")
            steam = root / "person/steam-engine/steam"
            self.assertEqual(os.readlink(steam / "compatibilitytools.d/proton-other-9"), str(proton))
            # A folder that names no tool, or an unsafe name, refuses the start.
            for text in ("", '"compatibilitytools"\n{\n  "compat_tools"\n  {\n    "../x"\n  }\n}\n'):
                (proton / "compatibilitytool.vdf").write_text(text)
                result = run()
                self.assertEqual(result.returncode, 1, text)
                self.assertEqual(json.loads(result.stdout)["reason"], "host_failed")

    def test_every_bare_command_of_the_wrapper_is_on_its_path(self):
        # The ACL test below needs ACLs, which the Nix build sandbox lacks;
        # this one reads the script and runs everywhere.
        builtins = {"cd", "exec", "exit", "export", "printf", "set", "trap", "true", "umask", "unset",
                    "for", "if", "in", "done", "fi", "say", "fail",
                    "local", "read", "return", "proton_tool_name"}
        found = set()
        for line in (HERE / "host-run.sh").read_text().splitlines():
            code = re.sub(r"'[^']*'", "''", re.sub(r"(^|\s)#.*", "", line))
            for segment in re.split(r"\$\(|\|\||&&|[;|`(!]|\b(?:then|do|else|if|while)\b", code):
                words = segment.split()
                while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
                    words = words[1:]
                if words and re.fullmatch(r"[a-z][a-z0-9_-]*", words[0]):
                    found.add(words[0])
        self.assertEqual(found - builtins - set(HOST_TOOLS), set())
        self.assertIn("setfacl", found)

    def test_with_only_its_runtime_inputs_the_wrapper_strips_korrid_from_engine_subfolders(self):
        # Device proof (RP Mini V2, 2026-11-20): "grep: command not found" on
        # every start, and compatdata, shadercache, common and the rest kept
        # user:korrid:r-- and default:user:korrid:r--.
        own = os.getuid()
        daemon = next((uid for uid in (0, 65534) if uid != own and _named(uid)), None)
        if daemon is None:
            self.skipTest("no named user other than this one")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steamapps = root / "person/steam-engine/steam/steamapps"
            inherited = [steamapps / "compatdata/401710/pfx", steamapps / "common/Game",
                         steamapps / "shadercache/401710"]
            for folder in inherited:
                folder.mkdir(parents=True)
            (steamapps / "common/Game/save.dat").write_text("x")
            (steamapps / "appmanifest_401710.acf").write_text(manifest_text())
            entry = f"u:{daemon}:r"
            setup = subprocess.run(["setfacl", "-R", "-m", entry, "-m", f"d:{entry}", str(steamapps)],
                                   capture_output=True, text=True)
            if setup.returncode != 0:
                self.skipTest(f"no ACLs on this file system: {setup.stderr.strip()}")
            # korrid owns the account folder (person/). The test cannot chown it, so
            # stat reports the daemon uid for that folder and nothing else.
            tools = root / "tools"
            tools.mkdir()
            real_stat = shutil.which("stat")
            for name in HOST_TOOLS:
                found = shutil.which(name)
                self.assertIsNotNone(found, name)
                if name != "stat":
                    (tools / name).symlink_to(found)
            (tools / "stat").write_text(
                f"#!{shutil.which('bash')}\n"
                f"if [[ \"$*\" == '-c %u {root / 'person'}' ]]; then echo {daemon}; exit 0; fi\n"
                f"exec {real_stat} \"$@\"\n")
            (tools / "stat").chmod(0o755)
            result, _, _, seen = self.start_host(root, path=str(tools))
            self.assertNotIn("command not found", result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue(seen.exists())

            def entries(path):
                text = subprocess.run(["getfacl", "-n", "-p", str(path)], capture_output=True,
                                      text=True, check=True).stdout
                return [line for line in text.splitlines() if f"user:{daemon}:" in line]

            for sub in ("common", "downloading", "compatdata", "shadercache", "temp", "workshop",
                        "sourcemods"):
                self.assertEqual(entries(steamapps / sub), [], sub)
            for path in [*inherited, steamapps / "common/Game/save.dat"]:
                self.assertEqual(entries(path), [], path)
            # korrid keeps traverse on the engine folder, listing on steam and
            # steamapps, and read on the manifests.
            engine = root / "person/steam-engine"
            self.assertEqual(entries(engine), [f"user:{daemon}:--x"])
            self.assertEqual(entries(engine / "steam"), [f"user:{daemon}:r-x"])
            self.assertEqual(entries(steamapps), [f"user:{daemon}:r-x", f"default:user:{daemon}:r--"])
            self.assertEqual(entries(steamapps / "appmanifest_401710.acf"), [f"user:{daemon}:r--"])


# What packages/engine.nix puts on the start wrapper's PATH: acl, coreutils,
# findutils, util-linux (flock). Every bare command in host-run.sh.
HOST_TOOLS = ["chmod", "dirname", "id", "ln", "mkdir", "stat", "find", "flock", "getfacl", "setfacl"]


def _named(uid):
    import pwd
    try:
        pwd.getpwuid(uid)
        return True
    except KeyError:
        return False


class EngineSessionTests(unittest.TestCase):
    def run_session(self, behavior="normal", entry=None, both=False, installed=(), files=("bin/game.exe",),
                    folders=(), prepare=None, legacycompat=("steamclient.dll", "steamclient64.dll", "Steam.dll"),
                    env_extra=None, answer=None, game_status=0):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        channel = root / "channel"
        channel.mkdir()
        os.mkfifo(channel / "commands", 0o600)
        engine = root / "person/steam-engine"
        steam = engine / "steam"
        (steam / "appcache").mkdir(parents=True)
        (steam / "steamapps/common/Game/bin").mkdir(parents=True)
        (engine / "home").mkdir()
        (steam / "steamapps/appmanifest_401710.acf").write_text(manifest_text(installed))
        app = (launch_config(*BOTH["entries"], depots=BOTH["depots"]) if both else launch_config(
            entry or {"executable": "bin\\game.exe", "arguments": "-x", "config": {"oslist": "windows"}}))
        (steam / "appcache/appinfo.vdf").write_bytes(appinfo({401710: app}))
        game_dir = steam / "steamapps/common/Game"
        for name in folders:
            (game_dir / name).mkdir(parents=True)
        for name in files:
            (game_dir / name).parent.mkdir(parents=True, exist_ok=True)
            (game_dir / name).write_text(
                f"#!{sys.executable}\nimport json, os, sys\n"
                f"open({str(Path(temporary.name) / 'game.json')!r}, 'w').write(json.dumps("
                "{'argv': sys.argv, 'native': True}))\n")
            (game_dir / name).chmod(0o755)
        if prepare:
            prepare(root, game_dir)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        notify = bin_dir / "systemd-notify"
        notify.write_text(f"#!{sys.executable}\nimport sys\nopen({str(root / 'statuses')!r}, 'a').write(sys.argv[1] + '\\n')\n")
        notify.chmod(0o755)
        fhs = root / "fhs/bin/korri-steam-engine-fhs"
        fhs.parent.mkdir(parents=True)
        fhs.write_text("#!/bin/sh\nexec \"$@\"\n")
        fhs.chmod(0o755)
        proton = root / "proton-tool"
        proton.mkdir()
        # korrid's ready legacycompat artifact (korri#589).
        artifact = root / "cache/legacycompat/1792618285"
        (artifact / "legacycompat").mkdir(parents=True)
        for name in legacycompat:
            (artifact / "legacycompat" / name).write_text("MZ")
        (proton / "proton").write_text(
            "import json, os, sys, time\n"
            f"open({str(root / 'game.json')!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd(), "
            "'legacycompat': os.path.realpath(os.environ['STEAM_COMPAT_CLIENT_INSTALL_PATH'] + '/legacycompat'), "
            "'env': {k: os.environ.get(k) for k in ('SteamAppId', 'STEAM_COMPAT_DATA_PATH', 'Steam3Master', 'HOME', "
            "'STEAM_COMPAT_TOOL_PATHS', 'SDL_JOYSTICK_HIDAPI_STEAMXBOX')}}))\n"
            "time.sleep(0.5)\n"
            f"sys.exit({game_status})\n")
        steps = subprocess.check_output(["bun", str(STEAM / "packages/session-steps.ts"), "engine"], text=True)
        (root / "steps.sh").write_text(steps)
        script = (HERE / "session.sh").read_text()
        for name, value in {"fhs": str(root / "fhs"), "steps": str(root / "steps.sh"),
                            "launchEntry": str(HERE / "launch-entry.py"),
                            "placeholder": str(HERE / "x-placeholder.py"),
                            "engineLibraryPath": "$steam/linuxarm64", "sdkLink": "sdkarm64"}.items():
            script = script.replace(f"@{name}@", value)
        (root / "session.sh").write_text(script)
        host = subprocess.Popen([sys.executable, "-c", HOST, str(channel), behavior])
        self.addCleanup(host.kill)
        # The game unit's PATH has exactly the package's runtime inputs and no
        # sh (device proof: "timeout: failed to run command 'sh'"). Give the
        # session only the commands those inputs provide.
        tools = root / "tools"
        tools.mkdir()
        for name in SESSION_TOOLS:
            found = shutil.which(name)
            self.assertIsNotNone(found, name)
            (tools / name).symlink_to(found)
        env = {**os.environ, "PATH": f"{bin_dir}:{tools}",
               "STEAM_ENGINE_HOME": str(engine), "KORRI_STEAM_ENGINE_CHANNEL": str(channel),
               "KORRI_PROTON_CACHYOS": str(proton), "KORRI_STEAM_LEGACYCOMPAT": str(artifact),
               "NOTIFY_SOCKET": str(root / "notify")}
        env.pop("DISPLAY", None)
        env.update(env_extra or {})
        if answer is not None:
            # korrid's answer, `delay` seconds after the question.
            line, delay = answer

            def reply():
                events = channel / "events.jsonl"
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if events.exists() and '"cloud_pending"' in events.read_text():
                        break
                    time.sleep(0.05)
                time.sleep(delay)
                with open(channel / "commands", "w") as fifo:
                    fifo.write(line + "\n")

            threading.Thread(target=reply, daemon=True).start()
        result = subprocess.run([shutil.which("bash"), str(root / "session.sh"), "401710"], env=env,
                                capture_output=True, text=True, timeout=60, check=False)
        self.root, self.channel = root, channel
        return result

    def wait_for(self, name, text):
        """The host stand-in reads the FIFO on its own; give it a moment."""
        path = self.channel / name
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists() and text in path.read_text():
                return path.read_text()
            time.sleep(0.05)
        return path.read_text() if path.exists() else ""

    def statuses(self):
        path = self.root / "statuses"
        return path.read_text().splitlines() if path.exists() else []

    def test_installs_syncs_plays_and_reports_the_exit(self):
        result = self.run_session()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.channel / "received").read_text(),
                         "install 401710\nlaunched 401710\nexited 401710\n")
        self.assertEqual(self.statuses(), ["--status=korri-step: update", "--status=korri-step: sync",
                                           "--status=korri-step: game"])
        game = json.loads((self.root / "game.json").read_text())
        steam = self.root / "person/steam-engine/steam"
        self.assertEqual(game["argv"], ["waitforexitandrun", f"{steam}/steamapps/common/Game/bin/game.exe", "-x"])
        self.assertEqual(game["cwd"], f"{steam}/steamapps/common/Game/bin")
        self.assertEqual(game["env"]["SteamAppId"], "401710")
        self.assertEqual(game["env"]["Steam3Master"], "127.0.0.1:57343")
        self.assertEqual(game["env"]["HOME"], str(self.root / "person/steam-engine/home"))
        self.assertEqual(game["env"]["STEAM_COMPAT_DATA_PATH"], f"{steam}/steamapps/compatdata/401710")
        # Proton finds Valve's legacycompat folder in the Steam folder (korri#589).
        self.assertEqual(game["legacycompat"], str(self.root / "cache/legacycompat/1792618285/legacycompat"))
        # The lock file names this session's cgroup for the host's pid translation.
        self.assertTrue((self.channel / "session.lock").read_text().startswith("/"))

    def test_a_game_that_stops_with_an_error_right_after_its_start_is_reported_as_failed(self):
        # korri#594: Korri showed such a session as completed.
        result = self.run_session(game_status=255)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((self.channel / "received").read_text(),
                         "install 401710\nlaunched 401710\nrefused game_failed\nexited 401710\n")
        self.assertEqual(self.statuses()[-1],
                         "--status=plugin-launch: Steam engine: the game stopped right after it started")

    def test_a_late_error_status_is_an_ordinary_end(self):
        # A game can end with a status other than 0 after hours of play.
        result = self.run_session(game_status=3, env_extra={"KORRI_STEAM_EARLY_EXIT_SECONDS": "0"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.channel / "received").read_text(),
                         "install 401710\nlaunched 401710\nexited 401710\n")

    def test_a_stale_legacycompat_link_moves_to_the_ready_artifact(self):
        def stale(root, game_dir):
            (root / "person/steam-engine/steam/legacycompat").symlink_to(root / "old/legacycompat")
        result = self.run_session(prepare=stale)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.started()["legacycompat"],
                         str(self.root / "cache/legacycompat/1792618285/legacycompat"))

    def test_without_the_steamclient_dlls_no_game_starts(self):
        result = self.run_session(legacycompat=("Steam.dll",))
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: Steam engine: the Steam client files are missing", self.statuses())
        self.assertFalse((self.root / "game.json").exists())

    def test_a_legacycompat_folder_that_is_not_a_link_is_left_alone(self):
        def folder(root, game_dir):
            (root / "person/steam-engine/steam/legacycompat").mkdir()
            (root / "person/steam-engine/steam/legacycompat/keep").write_text("x")
        result = self.run_session(prepare=folder)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertTrue((self.root / "person/steam-engine/steam/legacycompat/keep").exists())
        self.assertFalse((self.root / "game.json").exists())

    def test_a_failed_install_is_reported_through_the_engine_host(self):
        result = self.run_session("install-fails")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertEqual(self.wait_for("received", "refused"),
                         "install 401710\nrefused install_failed\n")
        self.assertIn("--status=plugin-launch: Steam engine: Steam could not install or update the game",
                      self.statuses())
        events = self.wait_for("events.jsonl", "launch_refused")
        self.assertIn('"event":"launch_refused","reason":"install_failed"', events)
        self.assertFalse((self.root / "game.json").exists())

    def test_a_missing_launch_entry_is_reported_through_the_engine_host(self):
        result = self.run_session(entry={"executable": "game.exe", "config": {"oslist": "macos"}})
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_a_linux_build_runs_its_linux_entry_natively(self):
        result = self.run_session(both=True, installed=(70301, 70303), files=("game.sh",))
        self.assertEqual(result.returncode, 0, result.stderr)
        game = json.loads((self.root / "game.json").read_text())
        self.assertTrue(game["native"])
        self.assertTrue(game["argv"][0].endswith("/Game/game.sh"))

    def test_a_missing_executable_is_never_started(self):
        # The Windows build is the installed one, but its .exe is not on disk.
        result = self.run_session(both=True, installed=(70301, 70302), files=())
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def windows_entry(self, executable, **fields):
        return {"executable": executable, "config": {"oslist": "windows"}, **fields}

    def started(self):
        return json.loads((self.root / "game.json").read_text())

    def game_dir(self):
        return self.root / "person/steam-engine/steam/steamapps/common/Game"

    def test_a_windows_entry_finds_its_executable_in_any_case(self):
        # Device proof (RP Mini V2, 2026-11-20): appinfo names vvvvvv.exe and
        # downwell.exe, the depots ship VVVVVV.exe and Downwell.exe.
        result = self.run_session(entry=self.windows_entry("downwell.exe"), files=("Downwell.exe",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.started()["argv"][:2], ["waitforexitandrun", str(self.game_dir() / "Downwell.exe")])
        self.assertEqual(self.started()["cwd"], str(self.game_dir()))

    def test_a_windows_entry_finds_a_nested_path_and_working_folder_in_any_case(self):
        result = self.run_session(
            entry=self.windows_entry("TOOLS\\x64\\GAME.EXE", workingdir="tools\\DATA"),
            files=("Tools/X64/Game.exe",), folders=("Tools/Data",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.started()["argv"][1], str(self.game_dir() / "Tools/X64/Game.exe"))
        self.assertEqual(self.started()["cwd"], str(self.game_dir() / "Tools/Data"))

    def test_a_windows_entry_prefers_the_exact_name(self):
        result = self.run_session(entry=self.windows_entry("game.exe"), files=("Game.exe", "game.exe"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.started()["argv"][1], str(self.game_dir() / "game.exe"))

    def test_a_windows_entry_with_two_names_in_other_case_starts_nothing(self):
        result = self.run_session(entry=self.windows_entry("game.exe"), files=("Game.exe", "GAME.EXE"))
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())

    def test_a_linux_entry_matches_exactly(self):
        app_entry = {"executable": "game.sh", "config": {"oslist": "linux"}}
        result = self.run_session(entry=app_entry, files=("Game.sh",))
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_a_missing_executable_in_any_case_is_never_started(self):
        result = self.run_session(entry=self.windows_entry("downwell.exe"), files=("Downwel.exe",))
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_an_entry_never_leads_out_of_the_install_folder(self):
        def outside(root, game_dir):
            other = game_dir.parent / "Other"
            other.mkdir()
            (other / "game.exe").write_text("x")
            (other / "game.exe").chmod(0o755)
            (root / "elsewhere").mkdir()
            (root / "elsewhere/game.exe").write_text("x")
            (game_dir / "link.exe").symlink_to(root / "elsewhere/game.exe")
            (game_dir / "linked").symlink_to(root / "elsewhere")
        for executable in ("..\\Other\\game.exe", "bin\\..\\..\\Other\\game.exe", "LINK.exe",
                           "linked\\game.exe", "/../Other/game.exe"):
            with self.subTest(executable=executable):
                result = self.run_session(entry=self.windows_entry(executable), files=(), prepare=outside)
                self.assertEqual(result.returncode, 126, result.stderr)
                self.assertFalse((self.root / "game.json").exists())
                self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_a_working_folder_never_leads_out_of_the_install_folder(self):
        result = self.run_session(entry=self.windows_entry("bin\\game.exe", workingdir="..\\..\\.."))
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())
        self.assertIn("refused game_files_missing", self.wait_for("received", "refused"))

    def test_a_symbolic_link_inside_the_install_folder_resolves_to_its_real_path(self):
        def link(root, game_dir):
            (game_dir / "Launcher.exe").symlink_to(game_dir / "bin/game.exe")
        result = self.run_session(entry=self.windows_entry("launcher.exe"), prepare=link)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.started()["argv"][1], str(self.game_dir() / "bin/game.exe"))

    def test_a_refused_host_start_ends_the_session_with_its_reason(self):
        result = self.run_session("host-failed")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: Steam engine: the engine host could not start", self.statuses())
        self.assertFalse((self.channel / "received").exists())

    def test_a_host_that_dies_silently_ends_the_session(self):
        # No logon_state ever comes; the free host lock is the only sign.
        started = time.monotonic()
        result = self.run_session("crash")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: Steam engine: the engine host stopped", self.statuses())
        self.assertIn("host lock free", result.stderr)
        self.assertLess(time.monotonic() - started, 30)

    def test_a_cloud_conflict_starts_no_game(self):
        result = self.run_session("conflict")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: steam-cloud-conflict", self.statuses())
        self.assertFalse((self.root / "game.json").exists())
        self.assertEqual((self.channel / "received").read_text(), "install 401710\nlaunched 401710\n")

    def test_a_pending_upload_on_another_device_holds_the_launch_until_the_answer(self):
        # The launch limit is 1 s (+10 s margin); the answer comes 3 s after it ran out.
        started = time.monotonic()
        result = self.run_session("pending", env_extra={"KORRI_STEAM_LAUNCH_SYNC_SECONDS": "1"},
                                  answer=("play-anyway 401710", 14))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(time.monotonic() - started, 14)
        self.assertIn("launch sync: downloaded", result.stderr)
        self.assertEqual((self.channel / "received").read_text(),
                         "install 401710\nlaunched 401710\nplay-anyway 401710\nexited 401710\n")
        self.assertTrue((self.root / "game.json").exists())
        self.assertEqual(self.statuses(), ["--status=korri-step: update", "--status=korri-step: sync",
                                           "--status=korri-step: game"])

    def test_an_engine_that_is_not_the_pinned_build_refuses_the_launch(self):
        result = self.run_session("mismatch")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: Steam engine: this engine build is not available on this device",
                      self.statuses())
        self.assertFalse((self.channel / "received").exists())


if __name__ == "__main__":
    unittest.main()
