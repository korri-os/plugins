"""Force shutdown before Cemu's real file-cache worker starts waiting."""

from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).resolve()
compiler = sys.argv[2]
text = (source / "src/Cemu/FileCache/FileCache.cpp").read_text()
writer = text.split("struct FileCacheAsyncJob", 1)[1].split(
    "#define FILECACHE_MAGIC_V1", 1
)[0]
writer = "struct FileCacheAsyncJob" + writer
assert writer.count("}FileCacheAsyncWriter;") == 1
writer = writer.replace("}FileCacheAsyncWriter;", "};")
notification = "m_fileCacheCondVar.notify_one();\n\t\t\tm_fileCacheThread.join();"
assert writer.count(notification) == 1
writer = writer.replace(
    notification,
    "m_fileCacheCondVar.notify_one();\n\t\t\tshutdown_notified.store(true);\n\t\t\tm_fileCacheThread.join();",
)
prefix = r"""
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <mutex>
#include <string>
#include <string_view>
#include <thread>
#include <vector>
using uint8 = std::uint8_t;
using uint32 = std::uint32_t;
using uint64 = std::uint64_t;
using sint32 = std::int32_t;
namespace fs = std::filesystem;
#include "FileCache.h"
// No jobs are submitted. Any file I/O would invalidate this lifecycle test.
void FileCache::AddFile(const FileName&&, const uint8*, sint32) { std::abort(); }
std::atomic_bool worker_entered{false}, release_worker{false}, destroyed{false}, shutdown_notified{false};
// The existing thread-naming seam gates the actual worker before its first wait.
void SetThreadName(const char*) {
    worker_entered.store(true);
    while (!release_worker.load()) std::this_thread::yield();
}
// The only observation added to the actual writer body is an atomic store
// after its real shutdown notification. No scheduling timeouts select the race.
"""
suffix = r"""
int main() {
    auto* writer = new _FileCacheAsyncWriter;
    while (!worker_entered.load()) std::this_thread::yield();
    std::thread destroyer([&] { delete writer; destroyed.store(true); });
    while (!shutdown_notified.load()) std::this_thread::yield();
    release_worker.store(true); // shutdown notification has already happened
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
    while (!destroyed.load() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::yield();
    if (!destroyed.load()) {
        std::fputs("FileCache worker lost its shutdown notification\n", stderr);
        std::_Exit(1);
    }
    destroyer.join();
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="cemu-filecache-shutdown-") as directory:
    root = Path(directory)
    harness = root / "shutdown.cpp"
    harness.write_text(prefix + writer + suffix)
    executable = root / "shutdown"
    subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-pthread",
            "-O2",
            "-I",
            str(source / "src/Cemu/FileCache"),
            str(harness),
            "-o",
            str(executable),
        ],
        check=True,
    )
    subprocess.run([executable], check=True, timeout=5)
print("Cemu actual FileCache early-shutdown interleaving passed")
