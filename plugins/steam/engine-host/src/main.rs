//! korri-steam-host: runs Valve's Steam engine (`steamclient.so`) for one Korri
//! session or job, with no Steam client and no Steam UI (Korri ADR 0083). Ported
//! from the spike `korri-steam-spike` (host v8, QR route B, map-driven build);
//! FINDINGS.md sections 1-11 there hold the evidence for every engine call.
//! No credential file, token or callback payload is printed, logged or written
//! by this program; the engine keeps its own login in its own Steam folder.
//!
//! korrid starts it (contract of #518):
//!   korri-steam-host --commands FIFO --host-lock FILE [--session-lock FILE] DIR/steamclient.so
//! with HOME = <person>/steam-engine/home, stdout appended to
//! <channel>/events.jsonl. With --session-lock the host serves one game session
//! (session mode); without it, one or more jobs (job mode).
//!
//! Start: with the empty public engine map the host reports
//! {"event":"engine_map_missing"} and exits 1. When the engine file's sha256 is
//! not the map's, it reports {"event":"engine_mismatch","expected":..,"found":..}
//! and exits 1 without loading the engine.
//!
//! Commands, one per line on the FIFO; one JSON event per line on stdout:
//!   launched <appid>   save_export, then the launch sync: start the queue,
//!                      evaluate, download remote changes together with the
//!                      AutoCloud launch pass, else run that pass alone
//!   exited <appid>     RunAutoCloudOnAppExit, start the queue, evaluate, upload,
//!                      then save_export
//!   sync <appid>       evaluate and upload
//!   install <appid>    InstallApp (also the update of an installed app), progress
//!   uninstall <appid>  UninstallApp
//!   resolve <appid> local|cloud
//!                      ResolveSyncConflict(appid, local), then wait for the job
//!   signin-qr          Steam's QR sign-in: qr_code, qr_refreshed, signed_in or
//!                      signin_failed
//!   signout            log off, forget the engine's saved login: signed_out, stop
//!   list-apps          one `app` event per licensed game, then `apps_done`
//!   shutdown           stop now, without waiting for an exit sync
//! Nothing runs in Steam Cloud when it is off for the account or the app. The
//! host only reads that setting. It resolves a conflict only on `resolve`.
//!
//! Logon: with a saved login (the account name file and the engine's own
//! ConnectCache) the network logon gets KORRI_STEAM_LOGON_SECONDS (default 15).
//! If it fails or times out, the host logs off and uses the engine's offline
//! logon when CanLogonOffline allows it; cloud commands then report "offline".
//! Without a saved login it reports `signin_required` and waits for `signin-qr`.
//!
//! Session mode (spike v7, FINDINGS.md section 10): the game session's shim holds
//! an exclusive flock on the session lock file for its whole life and writes its
//! cgroup into it. When the host can take the lock after it was held, the session
//! is gone: every app with `launched` and no `exited` gets an implied `exited`,
//! so its exit sync runs even when the shim was killed; then the host stops.
//! The host exports `kill`, so the engine's game-process check sees the game
//! unit's pids (PrivatePIDs). The host ends with `_exit` after its last output.
mod appinfo;
mod qr;
mod saves;

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::{c_char, c_int, c_long, c_void, CStr, CString, OsString},
    fs::{File, OpenOptions},
    io::{BufRead, BufReader, Read, Write},
    os::{
        fd::{AsRawFd, FromRawFd},
        unix::{
            ffi::OsStrExt,
            fs::{FileTypeExt, OpenOptionsExt},
        },
    },
    path::{Path, PathBuf},
    ptr,
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc, Mutex,
    },
    thread,
    time::{Duration, Instant},
};

type Object = *mut c_void;
static STOP: AtomicBool = AtomicBool::new(false);
extern "C" fn stop(_: c_int) {
    STOP.store(true, Ordering::Relaxed);
}
#[link(name = "dl")]
unsafe extern "C" {
    fn dlopen(path: *const c_char, flags: c_int) -> Object;
    fn dlsym(handle: Object, name: *const c_char) -> Object;
    fn dlerror() -> *const c_char;
    fn dladdr(addr: Object, info: *mut DlInfo) -> c_int;
}
unsafe extern "C" {
    fn dup(fd: c_int) -> c_int;
    fn dup2(old: c_int, new: c_int) -> c_int;
    fn signal(sig: c_int, handler: usize) -> usize;
    fn flock(fd: c_int, operation: c_int) -> c_int;
    fn syscall(number: c_long, ...) -> c_long;
    fn _exit(status: c_int) -> !;
    fn mkfifo(path: *const c_char, mode: u32) -> c_int;
}
#[cfg(target_arch = "aarch64")]
const SYS_KILL: c_long = 129;
#[cfg(target_arch = "x86_64")]
const SYS_KILL: c_long = 62;

// v7, host outside the game unit: the game runs in the game unit's PID
// namespace (PrivatePIDs=yes); the host runs in the user manager's. The engine
// checks each game process it tracks with kill(pid, 0) and then waitid
// (0x18c8ce0, called from 0xc67924, which logs "no longer tracking PID"), using
// the pid the game reported over IPC. Without help that pid names no process
// here, the engine drops the game at once and the game stops with "stalled
// cross-thread pipe (pipe is disconnected)". The build exports `kill` from this
// executable (build.rs), so the engine's kill@plt binds to the function below,
// which first translates a pid of the session to this PID namespace.
// The session is the game unit's cgroup: its cgroup.procs lists the unit's
// processes with pids of this namespace, and each /proc/PID/status NSpid line
// ends with the pid inside the unit. Both files are world-readable; the host's
// bwrap user namespace cannot read another process's /proc/PID/ns links.
/// The cgroup of the session lock's holder (the game unit), while held.
/// The engine's threads call `kill`; the main loop sets this at each probe.
static SESSION_CGROUP: Mutex<Option<String>> = Mutex::new(None);
/// Translations made: (session pid, host pid), first use order, for the JSON report.
static SESSION_PIDS: Mutex<Vec<(i32, i32)>> = Mutex::new(Vec::new());
#[no_mangle]
pub extern "C" fn kill(pid: c_int, sig: c_int) -> c_int {
    let cgroup = SESSION_CGROUP.lock().ok().and_then(|c| c.clone());
    let target = match cgroup.and_then(|c| session_pid(&c, pid)) {
        Some(host_pid) => {
            if let Ok(mut seen) = SESSION_PIDS.lock() {
                if !seen.contains(&(pid, host_pid)) {
                    seen.push((pid, host_pid));
                }
            }
            host_pid
        }
        None => pid,
    };
    // SAFETY: the kill system call with plain integer arguments; errno is set
    // by the libc syscall wrapper as kill(2) would set it.
    unsafe { syscall(SYS_KILL, target as c_long, sig as c_long) as c_int }
}
/// The pid, in this PID namespace, of the process in `cgroup` whose innermost
/// pid is `pid`.
fn session_pid(cgroup: &str, pid: c_int) -> Option<c_int> {
    if pid <= 0 {
        return None;
    }
    let procs = std::fs::read_to_string(format!("/sys/fs/cgroup{cgroup}/cgroup.procs")).ok()?;
    procs.lines().find_map(|host_pid| {
        let status = std::fs::read_to_string(format!("/proc/{}/status", host_pid.trim())).ok()?;
        nspid_match(&status, pid)
    })
}
/// From /proc/PID/status: the first NSpid entry (this namespace) when the last
/// (innermost) entry is `pid` and the process is in a nested namespace.
fn nspid_match(status: &str, pid: c_int) -> Option<c_int> {
    let line = status.lines().find_map(|l| l.strip_prefix("NSpid:"))?;
    let pids: Vec<c_int> = line
        .split_ascii_whitespace()
        .map(str::parse)
        .collect::<Result<_, _>>()
        .ok()?;
    match pids[..] {
        [first, .., last] if last == pid => Some(first),
        _ => None,
    }
}
/// The session's cgroup, as the shim writes it into the session lock file
/// after it took the lock (the path of its "0::" line in /proc/self/cgroup).
/// /proc/locks cannot name the holder: it keeps the pid of the flock(1)
/// process that took the lock for the shim's descriptor, which has exited.
fn session_cgroup_from(content: &str) -> Option<String> {
    let line = content.lines().next()?.trim();
    let valid = line.starts_with('/')
        && line.len() > 1
        && !line.split('/').any(|part| part == "..")
        && line
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"/-_.@:".contains(&b));
    valid.then(|| line.to_string())
}
const LOCK_EX: c_int = 2;
const LOCK_NB: c_int = 4;
const LOCK_UN: c_int = 8;
#[repr(C)]
struct DlInfo {
    name: *const c_char,
    base: Object,
    symbol: *const c_char,
    address: Object,
}
#[repr(C)]
#[derive(Default)]
struct Callback {
    user: i32,
    id: i32,
    data: *mut c_void,
    size: i32,
}

type CreateGlobal = unsafe extern "C" fn(Object, *mut i32) -> i32;
type ReleaseUser = unsafe extern "C" fn(Object, i32, i32);
type ReleasePipe = unsafe extern "C" fn(Object, i32) -> bool;
type GetUser = unsafe extern "C" fn(Object, i32, i32) -> Object;
type CommandLine = unsafe extern "C" fn(Object, i32, *mut *mut c_char);
type NoArgs = unsafe extern "C" fn(Object);
type BoolQuery = unsafe extern "C" fn(Object) -> bool;
type StateQuery = unsafe extern "C" fn(Object) -> i32;
type GetSteamId = unsafe extern "C" fn(Object) -> u64;
type CachedQuery = unsafe extern "C" fn(Object, *const c_char) -> bool;
type SelectCached = unsafe extern "C" fn(Object, *const c_char, bool) -> bool;
type LogOn = unsafe extern "C" fn(Object, u64) -> i32;
// IClientUser::SetLoginToken(token, accountName), no reply (spike results/qr).
type SetLoginToken = unsafe extern "C" fn(Object, *const c_char, *const c_char);
// uint32 IClientUser::GetSubscribedApps(AppId_t *list, uint32 max, bool includeFree):
// the proxy (1792618285: aa7ce0) sends max (4 bytes) and the bool (1 byte), reads
// the total (4 bytes), then min(total, max) * 4 bytes into `list`.
type SubscribedApps = unsafe extern "C" fn(Object, *mut u32, u32, bool) -> u32;
type GetCallback = unsafe extern "C" fn(i32, *mut Callback) -> bool;
// IClientUser slots 214 and 215 (offline-evidence.txt): both return an EResult.
type CanLogonOffline = unsafe extern "C" fn(Object) -> i32;
type LogOnOffline = unsafe extern "C" fn(Object, bool) -> i32;
type FreeCallback = unsafe extern "C" fn(i32);
// IClientRemoteStorage (IPC proxy), cloud-evidence.txt sections 5 to 7.
type EvaluateSyncState = unsafe extern "C" fn(Object, u32, bool);
type AppSyncState = unsafe extern "C" fn(Object, u32) -> u32;
type SynchronizeApp = unsafe extern "C" fn(Object, u32, u32, u64) -> bool;
type AppQuery = unsafe extern "C" fn(Object, u32) -> bool;
type AppCall = unsafe extern "C" fn(Object, u32);
type ResolveConflict = unsafe extern "C" fn(Object, u32, bool) -> bool;
type ConflictTimestamps = unsafe extern "C" fn(Object, u32, *mut u32, *mut u32) -> bool;
// IClientAppManager (IPC proxy), install-evidence.txt.
type InstallApp = unsafe extern "C" fn(Object, u32, i32, bool) -> u32;
type AppUpdateCall = unsafe extern "C" fn(Object, u32) -> u32;
type GetUpdateInfo = unsafe extern "C" fn(Object, u32, *mut u8) -> bool;
type U32Query = unsafe extern "C" fn(Object) -> u32;

// Engine map (scripts/aka/remap/remap; build.rs turns it into constants). Every
// slot index and RVA below comes from the map of one steamclient.so build:
// IClientEngine slots ENGINE_* (CSteamClient primary vtable), the IClientUserMap,
// IClientRemoteStorageMap and IClientAppManagerMap IPC proxies (USER_*, the cloud
// and app constants), each as (slot, RVA). The map's evidence is in remap's
// report.txt; FINDINGS.md sections 1-2 and 5-11 explain the methods.
// The getters (ENGINE_GET_*) return the IPC proxies: remap checks that the
// interface-set builder stores the proxy at the field each getter returns.
mod engine_map {
    include!(concat!(env!("OUT_DIR"), "/engine_map.rs"));
}
use engine_map::*;
// SynchronizeApp direction argument. CUser::PerformSyncCloud passes 2 next to
// "syncing local files to cloud" and 1 next to "syncing cloud files locally";
// SynchronizeApp turns 1 into the "down" command bit and 2 into "up".
const SYNC_DOWNLOAD: u32 = 1;
const SYNC_UPLOAD: u32 = 2;
// SynchronizeApp flags bit 1 adds the "AC Launch" command bit. With "down" the
// job runs as "AC Launch,down,", the job Valve's client logs at game start.
const SYNC_FLAG_AUTOCLOUD_LAUNCH: u64 = 2;

// IClientAppManager (install-evidence.txt): InstallApp(AppId_t, int32 libraryFolder,
// bool) installs to the default folder for a negative folder and, with the bool
// false, queues the app in the download scheduler. UninstallApp(AppId_t) returns 18
// when the app has no install record. GetAppInstallState(AppId_t) returns the app
// record's state flags ("StateFlags"; 1 without a record). GetUpdateInfo(AppId_t,
// 248-byte out) copies the record's update info.
// InstallApp library folder: negative = the default folder.
const DEFAULT_LIBRARY_FOLDER: i32 = -1;
// EAppUpdateError 0 = no error (InstallApp's success paths return 0).
const APP_UPDATE_OK: u32 = 0;
// UninstallApp's return when no install record exists (0x570874).
const APP_UPDATE_NOT_INSTALLED: u32 = 18;
const UPDATE_INFO_SIZE: usize = 248;
// Offsets in the 248-byte update info, from the appmanifest loader (0x5b4960,
// x22 = record+0x148): "BytesDownloaded" +0x80, "BytesToDownload" +0x88,
// "BytesStaged" +0x98, "BytesToStage" +0xa0, "UpdateResult" (record+0x184) +0x3c.
const UPDATE_INFO_BYTES_DOWNLOADED: usize = 0x80;
const UPDATE_INFO_BYTES_TO_DOWNLOAD: usize = 0x88;
const UPDATE_INFO_BYTES_STAGED: usize = 0x98;
const UPDATE_INFO_BYTES_TO_STAGE: usize = 0xa0;
const UPDATE_INFO_UPDATE_RESULT: usize = 0x3c;

// All slots are zero-based, without a destructor adjustment (this interface has none).
// SAFETY of all slot accesses below: only the engine build of the map is accepted; the
// object's vptr and each used slot are checked against the map's RVAs.
unsafe fn slot<T: Copy>(object: Object, index: usize) -> T {
    assert_eq!(std::mem::size_of::<T>(), std::mem::size_of::<usize>());
    unsafe { std::mem::transmute_copy(&(*object.cast::<*const usize>()).add(index).read()) }
}
unsafe fn check_slots(object: Object, base: usize, slots: &[(usize, usize)]) -> Result<(), String> {
    if object.is_null() {
        return Err("engine returned a null interface".into());
    }
    for &(index, rva) in slots {
        let actual: usize = unsafe { slot(object, index) };
        if actual != base + rva {
            return Err(format!(
                "unsupported steamclient interface: slot {index} does not match the engine map (sha256 {ENGINE_SHA256})"
            ));
        }
    }
    Ok(())
}
fn cstring(value: &[u8], label: &str) -> Result<CString, String> {
    CString::new(value).map_err(|_| format!("{label} contains a NUL byte"))
}
fn install_signals() -> Result<(), String> {
    for sig in [15, 2] {
        // SAFETY: stop uses only a lock-free atomic, and has the C signal ABI.
        if unsafe { signal(sig, stop as *const () as usize) } == usize::MAX {
            return Err("could not install signal handler".into());
        }
    }
    Ok(())
}
fn owned_fd(fd: i32) -> Result<File, String> {
    // SAFETY: dup returns a new, uniquely owned descriptor.
    let copy = unsafe { dup(fd) };
    if copy < 0 {
        return Err("could not duplicate output descriptor".into());
    }
    Ok(unsafe { File::from_raw_fd(copy) })
}
/// A JSON string literal, quotes included.
fn json_string(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}
fn json(out: &mut File, line: &str) -> Result<(), String> {
    writeln!(out, "{line}")
        .and_then(|_| out.flush())
        .map_err(|_| "JSON output failed".into())
}

#[derive(Debug, PartialEq, Eq)]
enum CommandSource {
    Stdin,
    Fifo(PathBuf),
}
#[derive(Debug, PartialEq, Eq)]
struct Args {
    library: Option<OsString>,
    commands: CommandSource,
    session_lock: Option<PathBuf>,
    host_lock: Option<PathBuf>,
}
const USAGE: &str = "usage: korri-steam-host [--commands FIFO] [--session-lock FILE] [--host-lock FILE] [absolute-steamclient.so-path]";
fn parse_args(args: Vec<OsString>) -> Result<Args, String> {
    let mut library = None;
    let mut commands = CommandSource::Stdin;
    let mut session_lock = None;
    let mut host_lock = None;
    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        let option = match arg.to_str() {
            Some("--commands") => None,
            Some("--session-lock") => Some(&mut session_lock),
            Some("--host-lock") => Some(&mut host_lock),
            _ if arg.as_bytes().starts_with(b"-") || library.is_some() => return Err(USAGE.into()),
            _ => {
                library = Some(arg);
                continue;
            }
        };
        let path = PathBuf::from(args.next().ok_or(USAGE)?);
        match option {
            None if commands == CommandSource::Stdin => commands = CommandSource::Fifo(path),
            Some(slot @ None) => *slot = Some(path),
            _ => return Err(USAGE.into()),
        }
    }
    Ok(Args {
        library,
        commands,
        session_lock,
        host_lock,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CloudCommand {
    Launched(u32),
    Exited(u32),
    Sync(u32),
    /// ResolveSyncConflict(appid, accept_local): `resolve <appid> local|cloud`.
    Resolve(u32, bool),
}
impl CloudCommand {
    fn name(self) -> &'static str {
        match self {
            CloudCommand::Launched(_) => "launched",
            CloudCommand::Exited(_) => "exited",
            CloudCommand::Sync(_) => "sync",
            CloudCommand::Resolve(..) => "resolve",
        }
    }
    fn appid(self) -> u32 {
        match self {
            CloudCommand::Launched(id)
            | CloudCommand::Exited(id)
            | CloudCommand::Sync(id)
            | CloudCommand::Resolve(id, _) => id,
        }
    }
}
/// v8: IClientAppManager commands (install-evidence.txt).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AppCommand {
    Install(u32),
    Uninstall(u32),
}
impl AppCommand {
    fn name(self) -> &'static str {
        match self {
            AppCommand::Install(_) => "install",
            AppCommand::Uninstall(_) => "uninstall",
        }
    }
    fn appid(self) -> u32 {
        match self {
            AppCommand::Install(id) | AppCommand::Uninstall(id) => id,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Command {
    Cloud(CloudCommand),
    App(AppCommand),
    /// Stop now: report open jobs as stopped, log off, exit.
    Shutdown,
    /// Steam's QR sign-in, when no account is signed in.
    SigninQr,
    /// Log off and forget the engine's saved login, then stop.
    Signout,
    /// Report the account's licensed games.
    ListApps,
    /// The session program refused the launch before the game started.
    Refused(Refusal),
}

/// Why steam-engine-session refused a launch, from a closed list: the
/// program sends only the word, and the host reports it with its own text,
/// so no line from the game unit is ever echoed. korrid reports `message`
/// as the session's failure (contract of korri#518: a wrapper such as
/// gamescope can end with 0 around the session program's refusal).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Refusal {
    SessionBusy,
    SigninTimeout,
    InstallTimeout,
    InstallFailed,
    NotInstalledOffline,
    NoLaunchEntry,
    GameFilesMissing,
}
impl Refusal {
    const ALL: [Refusal; 7] = [
        Refusal::SessionBusy,
        Refusal::SigninTimeout,
        Refusal::InstallTimeout,
        Refusal::InstallFailed,
        Refusal::NotInstalledOffline,
        Refusal::NoLaunchEntry,
        Refusal::GameFilesMissing,
    ];
    fn name(self) -> &'static str {
        match self {
            Refusal::SessionBusy => "session_busy",
            Refusal::SigninTimeout => "signin_timeout",
            Refusal::InstallTimeout => "install_timeout",
            Refusal::InstallFailed => "install_failed",
            Refusal::NotInstalledOffline => "not_installed_offline",
            Refusal::NoLaunchEntry => "no_launch_entry",
            Refusal::GameFilesMissing => "game_files_missing",
        }
    }
    /// The words the person sees; the same as the session program's own
    /// STATUS=plugin-launch text.
    fn message(self) -> &'static str {
        match self {
            Refusal::SessionBusy => "Steam engine: another session holds this launch",
            Refusal::SigninTimeout => "Steam engine: no Steam sign-in",
            Refusal::InstallTimeout => "Steam engine: the game update did not finish",
            Refusal::InstallFailed => "Steam engine: Steam could not install or update the game",
            Refusal::NotInstalledOffline => {
                "Steam engine: the game is not installed and Steam is offline"
            }
            Refusal::NoLaunchEntry => "Steam engine: Steam has no launch entry for this game",
            Refusal::GameFilesMissing => "Steam engine: the game files are missing",
        }
    }
    fn parse(word: &str) -> Option<Refusal> {
        Refusal::ALL.into_iter().find(|r| r.name() == word)
    }
}
// Errors name the fault only. The input line is never echoed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommandError {
    UnknownCommand,
    MissingAppId,
    InvalidAppId,
    ExtraArguments,
    LineTooLong,
    NotUtf8,
    /// `resolve` without `local` or `cloud`.
    InvalidSide,
    /// `refused` without a known reason word.
    InvalidReason,
}
impl CommandError {
    fn name(self) -> &'static str {
        match self {
            CommandError::UnknownCommand => "unknown_command",
            CommandError::MissingAppId => "missing_appid",
            CommandError::InvalidAppId => "invalid_appid",
            CommandError::ExtraArguments => "extra_arguments",
            CommandError::LineTooLong => "line_too_long",
            CommandError::NotUtf8 => "not_utf8",
            CommandError::InvalidSide => "invalid_side",
            CommandError::InvalidReason => "invalid_reason",
        }
    }
}
const MAX_COMMAND_LINE: usize = 256;
/// Blank lines give Ok(None).
fn parse_command(line: &str) -> Result<Option<Command>, CommandError> {
    let mut words = line.split_ascii_whitespace();
    let Some(verb) = words.next() else {
        return Ok(None);
    };
    let bare = |command| {
        if words.clone().next().is_some() {
            Err(CommandError::ExtraArguments)
        } else {
            Ok(Some(command))
        }
    };
    let make: fn(u32) -> Command = match verb {
        "launched" => |id| Command::Cloud(CloudCommand::Launched(id)),
        "exited" => |id| Command::Cloud(CloudCommand::Exited(id)),
        "sync" => |id| Command::Cloud(CloudCommand::Sync(id)),
        "install" => |id| Command::App(AppCommand::Install(id)),
        "uninstall" => |id| Command::App(AppCommand::Uninstall(id)),
        "resolve" => |id| Command::Cloud(CloudCommand::Resolve(id, false)),
        "shutdown" => return bare(Command::Shutdown),
        "signin-qr" => return bare(Command::SigninQr),
        "signout" => return bare(Command::Signout),
        "list-apps" => return bare(Command::ListApps),
        "refused" => {
            let refusal = words
                .next()
                .and_then(Refusal::parse)
                .ok_or(CommandError::InvalidReason)?;
            return if words.next().is_some() {
                Err(CommandError::ExtraArguments)
            } else {
                Ok(Some(Command::Refused(refusal)))
            };
        }
        _ => return Err(CommandError::UnknownCommand),
    };
    let appid = words.next().ok_or(CommandError::MissingAppId)?;
    let side = if verb == "resolve" {
        match words.next() {
            Some("local") => Some(true),
            Some("cloud") => Some(false),
            _ => return Err(CommandError::InvalidSide),
        }
    } else {
        None
    };
    if words.next().is_some() {
        return Err(CommandError::ExtraArguments);
    }
    if !appid.bytes().all(|b| b.is_ascii_digit()) {
        return Err(CommandError::InvalidAppId);
    }
    match (appid.parse::<u32>(), side) {
        (Ok(0) | Err(_), _) => Err(CommandError::InvalidAppId),
        (Ok(id), Some(local)) => Ok(Some(Command::Cloud(CloudCommand::Resolve(id, local)))),
        (Ok(id), None) => Ok(Some(make(id))),
    }
}
type CommandResult = Result<Command, CommandError>;
/// Reads lines until EOF; Err(()) when the receiver is gone.
fn read_commands(
    reader: &mut impl BufRead,
    sender: &mpsc::Sender<CommandResult>,
) -> Result<(), ()> {
    let mut line = Vec::new();
    loop {
        line.clear();
        let limit = MAX_COMMAND_LINE as u64 + 1;
        match reader.by_ref().take(limit).read_until(b'\n', &mut line) {
            Ok(0) | Err(_) => return Ok(()),
            Ok(_) => {}
        }
        let parsed = if line.len() > MAX_COMMAND_LINE && line.last() != Some(&b'\n') {
            // Discard the rest of an oversized line without buffering it.
            let _ = reader.skip_until(b'\n');
            Err(CommandError::LineTooLong)
        } else {
            match std::str::from_utf8(&line).map(parse_command) {
                Err(_) => Err(CommandError::NotUtf8),
                Ok(Ok(None)) => continue,
                Ok(Ok(Some(command))) => Ok(command),
                Ok(Err(error)) => Err(error),
            }
        };
        sender.send(parsed).map_err(|_| ())?;
    }
}
fn spawn_command_reader(source: CommandSource, sender: mpsc::Sender<CommandResult>) {
    // The thread is never joined; it may stay blocked in read or open until exit.
    thread::spawn(move || match source {
        CommandSource::Stdin => {
            let _ = read_commands(&mut std::io::stdin().lock(), &sender);
        }
        CommandSource::Fifo(path) => loop {
            // Each writer opens, writes and closes; then wait for the next one.
            let Ok(fifo) = File::open(&path) else { return };
            if read_commands(&mut BufReader::new(fifo), &sender).is_err() {
                return;
            }
        },
    });
}

/// ERemoteStorageSyncState names, from the branches of CUser::PerformSyncCloud
/// (0xc8f8a8) and its log strings; 3 is returned when IsAppSyncInProgress is true.
/// cloud4-evidence.txt: 0 = cloud off or no quota, 1 = cache loaded but not yet
/// compared with the server in this engine session, 8 = app not in the cache map;
/// 4, 5, 6 and 7 come from per-file states (remote, local, both, conflict).
fn sync_state_name(state: u32) -> &'static str {
    match state {
        0 => "none",
        1 => "unknown",
        2 => "synchronized",
        3 => "in_progress",
        4 => "remote_changes",
        5 => "local_changes",
        6 => "local_and_remote_changes",
        7 => "conflict",
        8 => "needs_evaluation",
        _ => "unhandled",
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum JobKind {
    Launch,
    Exit,
    Sync,
    /// ResolveSyncConflict was called; wait for its job.
    Resolve,
}
impl JobKind {
    fn name(self) -> &'static str {
        match self {
            JobKind::Launch => "launch",
            JobKind::Exit => "exit",
            JobKind::Sync => "sync",
            JobKind::Resolve => "resolve",
        }
    }
}
/// Engine calls a command makes before its first poll, in order, and the calls
/// of the AutoCloud launch pass when a launch has nothing to download.
/// RunAutoCloudOnAppLaunch/Exit only set a command bit on the app's queue entry;
/// they do not start a job. LoadLocalFileInfoCache adds "init" and starts the
/// queue without the cloud quota check that Evaluate and SynchronizeApp make.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CloudCall {
    RunAutoCloudOnAppLaunch,
    RunAutoCloudOnAppExit,
    LoadLocalFileInfoCache,
}
impl CloudCall {
    fn name(self) -> &'static str {
        match self {
            CloudCall::RunAutoCloudOnAppLaunch => "RunAutoCloudOnAppLaunch",
            CloudCall::RunAutoCloudOnAppExit => "RunAutoCloudOnAppExit",
            CloudCall::LoadLocalFileInfoCache => "LoadLocalFileInfoCache",
        }
    }
    fn slot(self) -> usize {
        match self {
            CloudCall::RunAutoCloudOnAppLaunch => RUN_AUTOCLOUD_ON_LAUNCH.0,
            CloudCall::RunAutoCloudOnAppExit => RUN_AUTOCLOUD_ON_EXIT.0,
            CloudCall::LoadLocalFileInfoCache => LOAD_LOCAL_FILE_INFO_CACHE.0,
        }
    }
}
fn first_calls(kind: JobKind) -> &'static [CloudCall] {
    use CloudCall::*;
    match kind {
        // The launch pass waits until the host knows whether to download.
        JobKind::Launch => &[LoadLocalFileInfoCache],
        JobKind::Exit => &[RunAutoCloudOnAppExit, LoadLocalFileInfoCache],
        // EvaluateRemoteStorageSyncState starts the queue itself.
        JobKind::Sync => &[],
        // ResolveSyncConflict starts the queue itself (d13fd0).
        JobKind::Resolve => &[],
    }
}
const AUTOCLOUD_LAUNCH_PASS: [CloudCall; 2] = [
    CloudCall::RunAutoCloudOnAppLaunch,
    CloudCall::LoadLocalFileInfoCache,
];
/// The person's Steam Cloud setting decides; the host never turns it on.
fn cloud_allowed(account: bool, app: bool) -> bool {
    account && app
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SyncStep {
    Wait,
    Evaluate,
    Upload,
    /// SynchronizeApp(download, AutoCloud launch): one "AC Launch,down," job.
    DownloadForLaunch,
    /// RunAutoCloudOnAppLaunch, then start the queue; the result to report after it.
    LaunchPass(&'static str),
    Finish(&'static str),
}
const MAX_EVALUATIONS: u8 = 2;
const MAX_UPLOADS: u8 = 2;
/// What a job has asked the engine for so far.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
struct Progress {
    evaluations: u8,
    uploads: u8,
    downloads: u8,
    /// Set when the AutoCloud launch pass was queued: the result to report after it.
    launch_pass: Option<&'static str>,
}
/// One decision for one app. The host never resolves a conflict and never
/// uploads at launch: a conflict ends the job and is reported for a person.
fn next_step(kind: JobKind, state: u32, in_progress: bool, progress: Progress) -> SyncStep {
    if in_progress || state == 3 {
        return SyncStep::Wait;
    }
    if kind == JobKind::Resolve {
        return next_resolve_step(state, progress);
    }
    if progress.evaluations == 0 {
        return SyncStep::Evaluate;
    }
    if kind == JobKind::Launch {
        return next_launch_step(state, progress);
    }
    match state {
        1 | 8 if progress.evaluations < MAX_EVALUATIONS => SyncStep::Evaluate,
        1 | 8 => SyncStep::Finish("evaluation_incomplete"),
        5 if progress.uploads < MAX_UPLOADS => SyncStep::Upload,
        5 => SyncStep::Finish("upload_incomplete"),
        2 => SyncStep::Finish("synchronized"),
        4 => SyncStep::Finish("remote_changes_not_downloaded"),
        6 => SyncStep::Finish("local_and_remote_changes_not_synced"),
        7 => SyncStep::Finish("conflict_not_resolved"),
        0 => SyncStep::Finish("no_sync_state"),
        _ => SyncStep::Finish("unhandled_state"),
    }
}
/// Resolve: the engine queued "up" or "down" with the overwrite bit (0x14/0x18,
/// FINDINGS.md section 7). Its job ends in state 2; evaluate if the cache is not
/// compared yet. A conflict that stays means the choice did not apply.
fn next_resolve_step(state: u32, progress: Progress) -> SyncStep {
    match state {
        2 => SyncStep::Finish("resolved"),
        1 | 8 if progress.evaluations < MAX_EVALUATIONS => SyncStep::Evaluate,
        1 | 8 => SyncStep::Finish("evaluation_incomplete"),
        7 => SyncStep::Finish("conflict_not_resolved"),
        5 if progress.uploads < MAX_UPLOADS => SyncStep::Upload,
        0 => SyncStep::Finish("no_sync_state"),
        _ => SyncStep::Finish("unhandled_state"),
    }
}
/// Launch: download remote changes before the game starts, as Valve's client
/// does with "AC Launch,down,". Local changes and conflicts keep the local files;
/// the AutoCloud launch pass still runs so the exit pass can find changed files.
fn next_launch_step(state: u32, progress: Progress) -> SyncStep {
    if let Some(result) = progress.launch_pass {
        return SyncStep::Finish(match state {
            7 => "conflict",
            _ => result,
        });
    }
    if progress.downloads > 0 {
        return SyncStep::Finish(match state {
            // 5: the remote files arrived; local changes wait for the exit upload.
            2 | 5 => "downloaded",
            7 => "conflict",
            0 => "no_sync_state",
            _ => "download_incomplete",
        });
    }
    match state {
        1 | 8 if progress.evaluations < MAX_EVALUATIONS => SyncStep::Evaluate,
        1 | 8 => SyncStep::Finish("evaluation_incomplete"),
        4 | 6 => SyncStep::DownloadForLaunch,
        2 => SyncStep::LaunchPass("synchronized"),
        5 => SyncStep::LaunchPass("local_changes"),
        7 => SyncStep::LaunchPass("conflict"),
        0 => SyncStep::Finish("no_sync_state"),
        _ => SyncStep::Finish("unhandled_state"),
    }
}
const POLL_INTERVAL: Duration = Duration::from_millis(250);
// Each proxy call waits for the engine's reply, and the engine adds the app's
// queue entry before it replies, so IsAppSyncInProgress is true when the call
// returns (cloud3-evidence.txt). One second only covers the unexpected case.
const START_GRACE: Duration = Duration::from_secs(1);
const JOB_TIMEOUT: Duration = Duration::from_secs(600);
// The game waits for the launch job; this limit lets it start anyway.
const DEFAULT_LAUNCH_TIMEOUT: Duration = Duration::from_secs(120);
const LAUNCH_TIMEOUT_VARIABLE: &str = "KORRI_STEAM_LAUNCH_SYNC_SECONDS";
const LAUNCH_TIMEOUT_MAX: u64 = 3600;
// The network logon gets this long before the host tries the engine's offline logon.
const DEFAULT_LOGON_TIMEOUT: Duration = Duration::from_secs(15);
const LOGON_TIMEOUT_VARIABLE: &str = "KORRI_STEAM_LOGON_SECONDS";
const LOGON_TIMEOUT_MAX: u64 = 300;
// After SIGTERM the host waits this long for `exited` and the exit sync. The
// maximum stays under systemd's default TimeoutStopSec of 90 s.
const DEFAULT_STOP_GRACE: Duration = Duration::from_secs(45);
const STOP_GRACE_VARIABLE: &str = "KORRI_STEAM_STOP_GRACE_SECONDS";
const STOP_GRACE_MAX: u64 = 80;
/// Delay between the stop signal and the implied `exited` for pending apps,
/// so the killed game's last writes reach disk first.
const STOP_IMPLIED_EXIT: Duration = Duration::from_secs(2);
/// A whole number of seconds from 1 to `max`; `None` (variable unset) gives `default`.
fn parse_seconds(
    variable: &str,
    value: Option<&str>,
    default: Duration,
    max: u64,
) -> Result<Duration, String> {
    let Some(value) = value else {
        return Ok(default);
    };
    match value.parse::<u64>() {
        Ok(seconds) if (1..=max).contains(&seconds) => Ok(Duration::from_secs(seconds)),
        _ => Err(format!(
            "{variable} must be a whole number of seconds from 1 to {max}"
        )),
    }
}

/// What the host does after SIGTERM/SIGINT. Apps that had `launched` and no
/// `exited` yet are pending: their game is still stopping, and its exit sync
/// must run before logoff.
#[derive(Debug, Clone, PartialEq, Eq)]
enum StopAction {
    Continue,
    StopNow,
    /// First signal with apps pending: report, then keep running until `deadline`.
    Wait {
        pending: Vec<u32>,
        grace: Duration,
    },
    /// The grace ran out with these apps still pending or a job still open.
    Expired {
        pending: Vec<u32>,
    },
}
struct StopControl {
    grace: Duration,
    running: BTreeSet<u32>,
    deadline: Option<Instant>,
}
impl StopControl {
    fn new(grace: Duration) -> Self {
        StopControl {
            grace,
            running: BTreeSet::new(),
            deadline: None,
        }
    }
    /// Every received command, in order, before it is queued or run.
    fn command(&mut self, command: CloudCommand) {
        match command {
            CloudCommand::Launched(appid) => {
                self.running.insert(appid);
            }
            CloudCommand::Exited(appid) => {
                self.running.remove(&appid);
            }
            CloudCommand::Sync(_) | CloudCommand::Resolve(..) => {}
        }
    }
    /// A stop signal. A repeated signal (systemd and the reaper both send one)
    /// changes nothing while the host already waits.
    fn signal(&mut self, now: Instant) -> StopAction {
        if self.deadline.is_some() {
            return StopAction::Continue;
        }
        if self.running.is_empty() {
            return StopAction::StopNow;
        }
        self.deadline = Some(now + self.grace);
        StopAction::Wait {
            pending: self.running.iter().copied().collect(),
            grace: self.grace,
        }
    }
    /// Each loop pass. `busy`: a cloud job runs or a command waits for the session.
    fn poll(&mut self, now: Instant, busy: bool) -> StopAction {
        let Some(deadline) = self.deadline else {
            return StopAction::Continue;
        };
        if self.running.is_empty() && !busy {
            return StopAction::StopNow;
        }
        if now >= deadline {
            return StopAction::Expired {
                pending: self.running.iter().copied().collect(),
            };
        }
        StopAction::Continue
    }
}
impl StopControl {
    /// Apps that had `launched` and no `exited` yet, in appid order.
    fn running(&self) -> Vec<u32> {
        self.running.iter().copied().collect()
    }
}

// v7: how often the host probes the session lock.
const SESSION_PROBE_INTERVAL: Duration = Duration::from_secs(1);
// With no session, no app and no job for this long, the host stops.
const DEFAULT_IDLE_TIMEOUT: Duration = Duration::from_secs(300);
const IDLE_TIMEOUT_VARIABLE: &str = "KORRI_STEAM_IDLE_SECONDS";
const IDLE_TIMEOUT_MAX: u64 = 3600;
// A shim tests host.lock with a short flock; the starting host retries that long.
const HOST_LOCK_WAIT: Duration = Duration::from_secs(5);
/// What one probe of the session lock means for the host.
#[derive(Debug, Clone, PartialEq, Eq)]
enum SessionAction {
    Continue,
    /// The lock was free while these apps had no `exited`: the session is gone.
    Ended {
        pending: Vec<u32>,
    },
    /// Free lock, no app, no job, for the whole idle timeout.
    IdleStop,
    /// Session mode: the session lock was held and is free again, and every exit
    /// sync is done. The host's session is over.
    Over,
}
/// `held`: another process holds the session lock. `seen`: it was held at
/// least once (session mode). `running`: apps with `launched` and no `exited`.
/// `busy`: a job runs or a command waits. `idle_since` is the start of the
/// current idle time; reset when not idle.
#[allow(clippy::too_many_arguments)]
fn session_step(
    idle_since: &mut Option<Instant>,
    idle_timeout: Duration,
    now: Instant,
    held: bool,
    seen: bool,
    running: Vec<u32>,
    busy: bool,
) -> SessionAction {
    if held || busy || !running.is_empty() {
        *idle_since = None;
        if !held && !running.is_empty() {
            return SessionAction::Ended { pending: running };
        }
        return SessionAction::Continue;
    }
    if seen {
        return SessionAction::Over;
    }
    let since = *idle_since.get_or_insert(now);
    if now.duration_since(since) >= idle_timeout {
        SessionAction::IdleStop
    } else {
        SessionAction::Continue
    }
}
/// Opens (creates, mode 0600) a lock file. The descriptor is close-on-exec, so
/// the engine's child processes never hold the lock.
fn open_lock(path: &PathBuf) -> Result<File, String> {
    use std::os::unix::fs::OpenOptionsExt;
    OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .mode(0o600)
        .open(path)
        .map_err(|_| "cannot open a lock file".into())
}
/// Takes the exclusive flock without waiting; false when another open file
/// description holds it.
fn try_lock(file: &File) -> bool {
    // SAFETY: flock on a descriptor this File owns.
    unsafe { flock(file.as_raw_fd(), LOCK_EX | LOCK_NB) == 0 }
}
fn unlock(file: &File) {
    // SAFETY: as above.
    unsafe { flock(file.as_raw_fd(), LOCK_UN) };
}
/// Takes the host lock, retrying for `wait` (a shim's probe holds it briefly).
fn take_host_lock(path: &PathBuf, wait: Duration) -> Result<File, String> {
    let file = open_lock(path)?;
    let deadline = Instant::now() + wait;
    while !try_lock(&file) {
        if Instant::now() >= deadline {
            return Err("another korri-steam-host holds the host lock".into());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Ok(file)
}
fn appid_list(appids: &[u32]) -> String {
    let items: Vec<String> = appids.iter().map(u32::to_string).collect();
    format!("[{}]", items.join(","))
}

/// Where the logon is. Only `Online` (signed in) and `Offline` run commands.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum LogonPhase {
    /// No saved login: waits for `signin-qr`.
    SignedOut,
    /// The QR sign-in runs on its own thread.
    Qr,
    /// LogOn was accepted; the engine connects and signs in.
    Connecting { deadline: Instant },
    /// Signed in to Steam once. A later connection loss is only reported; the
    /// engine reconnects by itself.
    Online,
    /// The network logon failed. LogOff was called (unless LogOn itself was
    /// refused); wait for logon state 0 before the offline logon.
    LeavingNetwork { deadline: Instant },
    /// LogOnOffline accepted. The host stays offline until it stops.
    Offline,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FallbackReason {
    /// No signed-in state within KORRI_STEAM_LOGON_SECONDS.
    Timeout,
    /// Callback 102 or 103 (SteamServersDisconnected_t, SteamServerConnectFailure_t).
    ConnectFailed(i32),
    /// LogOn returned this EResult instead of 1; no LogOff is needed.
    LogOnRefused(i32),
}
impl FallbackReason {
    fn json(self) -> String {
        match self {
            FallbackReason::Timeout => r#""reason":"timeout""#.to_string(),
            FallbackReason::ConnectFailed(id) => {
                format!(r#""reason":"connect_failed","callback":{id}"#)
            }
            FallbackReason::LogOnRefused(result) => {
                format!(r#""reason":"logon_refused","eresult":{result}"#)
            }
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ConnectStep {
    Wait,
    Online,
    Fallback(FallbackReason),
}
/// One decision while connecting. A signed-in state wins over a failure seen
/// in the same pass, because the engine retries by itself.
fn connecting_step(
    now: Instant,
    deadline: Instant,
    logged_on: bool,
    connect_failure: Option<i32>,
) -> ConnectStep {
    if logged_on {
        ConnectStep::Online
    } else if let Some(id) = connect_failure {
        ConnectStep::Fallback(FallbackReason::ConnectFailed(id))
    } else if now >= deadline {
        ConnectStep::Fallback(FallbackReason::Timeout)
    } else {
        ConnectStep::Wait
    }
}
// LogOff after a failed network logon gets this long to reach logon state 0.
const LEAVE_NETWORK_TIMEOUT: Duration = Duration::from_secs(5);
fn left_network(now: Instant, deadline: Instant, logon_state: i32) -> bool {
    logon_state == 0 || now >= deadline
}
/// Commands run only in a signed-in online session or an offline session.
fn session_ready(phase: LogonPhase, logged_on: bool) -> bool {
    match phase {
        LogonPhase::Online => logged_on,
        LogonPhase::Offline => true,
        LogonPhase::Connecting { .. }
        | LogonPhase::LeavingNetwork { .. }
        | LogonPhase::SignedOut
        | LogonPhase::Qr => false,
    }
}
// EResult k_EResultOK. CanLogonOffline and LogOnOffline return EResult
// (their proxies return 55, k_EResultRemoteCallFailed, when the IPC call fails).
const ERESULT_OK: i32 = 1;
// LogOnOffline's bool is stored as the engine's offline-mode flag (the byte that
// LogOn checks before "LogOn() called, but user is in offline mode.").
const OFFLINE_MODE: bool = true;
// While online, report CanLogonOffline on change at this interval.
const OFFLINE_CHECK_INTERVAL: Duration = Duration::from_secs(30);
struct SyncJob {
    kind: JobKind,
    started: Instant,
    next_poll: Instant,
    awaiting_start_until: Option<Instant>,
    progress: Progress,
    reported: Option<(u32, bool)>,
}
struct RemoteStorage {
    object: Object,
}
impl RemoteStorage {
    // SAFETY for all methods: the object's vptr and these slots were checked
    // against the engine map when the object was obtained.
    fn evaluate(&self, appid: u32) {
        let call: EvaluateSyncState = unsafe { slot(self.object, EVALUATE_SYNC_STATE.0) };
        unsafe { call(self.object, appid, false) }
    }
    fn state(&self, appid: u32) -> u32 {
        let call: AppSyncState = unsafe { slot(self.object, GET_SYNC_STATE.0) };
        unsafe { call(self.object, appid) }
    }
    fn upload(&self, appid: u32) -> bool {
        let call: SynchronizeApp = unsafe { slot(self.object, SYNCHRONIZE_APP.0) };
        unsafe { call(self.object, appid, SYNC_UPLOAD, 0) }
    }
    fn download_for_launch(&self, appid: u32) -> bool {
        let call: SynchronizeApp = unsafe { slot(self.object, SYNCHRONIZE_APP.0) };
        unsafe {
            call(
                self.object,
                appid,
                SYNC_DOWNLOAD,
                SYNC_FLAG_AUTOCLOUD_LAUNCH,
            )
        }
    }
    /// (found, newest local "time", newest remote "remotetime") of conflicting files.
    fn conflict_timestamps(&self, appid: u32) -> (bool, u32, u32) {
        let call: ConflictTimestamps =
            unsafe { slot(self.object, GET_CONFLICTING_FILE_TIMESTAMPS.0) };
        let (mut local, mut remote) = (0u32, 0u32);
        let found = unsafe { call(self.object, appid, &mut local, &mut remote) };
        (found, local, remote)
    }
    /// bool ResolveSyncConflict(AppId_t, bool acceptLocal): true keeps this
    /// device's files and uploads them, false takes the cloud's.
    fn resolve(&self, appid: u32, local: bool) -> bool {
        let call: ResolveConflict = unsafe { slot(self.object, RESOLVE_SYNC_CONFLICT.0) };
        unsafe { call(self.object, appid, local) }
    }
    fn in_progress(&self, appid: u32) -> bool {
        let call: AppQuery = unsafe { slot(self.object, IS_APP_SYNC_IN_PROGRESS.0) };
        unsafe { call(self.object, appid) }
    }
    fn call(&self, call: CloudCall, appid: u32) {
        let function: AppCall = unsafe { slot(self.object, call.slot()) };
        unsafe { function(self.object, appid) }
    }
    fn account_cloud_enabled(&self) -> bool {
        let call: BoolQuery = unsafe { slot(self.object, IS_CLOUD_ENABLED_FOR_ACCOUNT.0) };
        unsafe { call(self.object) }
    }
    fn app_cloud_enabled(&self, appid: u32) -> bool {
        let call: AppQuery = unsafe { slot(self.object, IS_CLOUD_ENABLED_FOR_APP.0) };
        unsafe { call(self.object, appid) }
    }
}
/// save_export (ADR 0083): one tar archive of the app's Steam Cloud set in the
/// launch channel, before the launch sync and after the exit sync. Games with no
/// Steam Cloud quota get none, as today.
struct SaveExports {
    /// <channel>/saves: korrid imports each archive it is told about.
    dir: PathBuf,
    steam: PathBuf,
    home: PathBuf,
    /// The signed-in account; 0 until the logon selected it.
    steam_id: u64,
    sequence: u32,
}
impl SaveExports {
    fn export(&mut self, out: &mut File, appid: u32, phase: &str) -> Result<(), String> {
        if self.steam_id == 0 {
            return Ok(());
        }
        let apps = std::fs::read(self.steam.join("appcache/appinfo.vdf"))
            .map_err(|_| "no appinfo.vdf".to_string())
            .and_then(|bytes| appinfo::read(&bytes));
        let app = match &apps {
            Ok(apps) => apps.get(&appid),
            Err(_) => None,
        };
        if !saves::has_cloud(app) {
            return Ok(());
        }
        let places = saves::Places {
            steam: &self.steam,
            home: &self.home,
            appid,
            steam_id: self.steam_id,
        };
        self.sequence += 1;
        let archive = self
            .dir
            .join(format!("{appid}-{phase}-{}.tar", self.sequence));
        let result = saves::collect(&places, app).and_then(|collected| {
            if collected.files.is_empty() {
                Ok(None)
            } else {
                saves::write_archive(&archive, &collected).map(|()| Some(collected))
            }
        });
        match result {
            Ok(Some(_)) => {
                let path = archive.to_string_lossy();
                json(
                    out,
                    &format!(
                        r#"{{"event":"save_export","appid":{appid},"archive":{}}}"#,
                        json_string(&path)
                    ),
                )
            }
            Ok(None) => json(
                out,
                &format!(r#"{{"event":"save_export_empty","appid":{appid},"phase":"{phase}"}}"#),
            ),
            Err(reason) => json(
                out,
                &format!(
                    r#"{{"event":"save_export_failed","appid":{appid},"phase":"{phase}","reason":{}}}"#,
                    json_string(&reason)
                ),
            ),
        }
    }
}
struct Cloud {
    storage: RemoteStorage,
    saves: SaveExports,
    jobs: BTreeMap<u32, SyncJob>,
    launch_timeout: Duration,
    /// Engine offline logon: no cloud call can work (the sync job requires logon
    /// state 4 and a clear offline-mode flag), so commands report "offline".
    offline: bool,
}
impl Cloud {
    fn finish(
        out: &mut File,
        appid: u32,
        job: &SyncJob,
        result: &str,
        state: Option<u32>,
    ) -> Result<(), String> {
        let state = state.map_or("null".to_string(), |s| s.to_string());
        json(
            out,
            &format!(
                r#"{{"event":"sync_finished","appid":{appid},"kind":"{}","result":"{result}","state":{state},"seconds":{}}}"#,
                job.kind.name(),
                job.started.elapsed().as_secs()
            ),
        )
    }
    fn call_event(out: &mut File, call: &str, appid: u32) -> Result<(), String> {
        json(
            out,
            &format!(r#"{{"event":"cloud_call","call":"{call}","appid":{appid}}}"#),
        )
    }
    fn start(&mut self, out: &mut File, command: CloudCommand) -> Result<(), String> {
        let appid = command.appid();
        let now = Instant::now();
        if let Some(old) = self.jobs.remove(&appid) {
            Self::finish(out, appid, &old, "superseded", None)?;
        }
        let kind = match command {
            CloudCommand::Launched(_) => JobKind::Launch,
            CloudCommand::Exited(_) => JobKind::Exit,
            CloudCommand::Sync(_) => JobKind::Sync,
            CloudCommand::Resolve(..) => JobKind::Resolve,
        };
        json(
            out,
            &format!(
                r#"{{"event":"sync_started","appid":{appid},"kind":"{}"}}"#,
                kind.name()
            ),
        )?;
        let job = SyncJob {
            kind,
            started: now,
            next_poll: now,
            // An AutoCloud call queues a pass; let it start before deciding.
            awaiting_start_until: (kind != JobKind::Sync).then_some(now + START_GRACE),
            progress: Progress::default(),
            reported: None,
        };
        if self.offline {
            // No cloud call can run offline; the saves still change.
            if kind == JobKind::Launch {
                self.saves.export(out, appid, "launch")?;
            }
            Self::finish(out, appid, &job, "offline", None)?;
            if kind == JobKind::Exit {
                self.saves.export(out, appid, "exit")?;
            }
            return Ok(());
        }
        let account = self.storage.account_cloud_enabled();
        let app = self.storage.app_cloud_enabled(appid);
        json(
            out,
            &format!(
                r#"{{"event":"cloud_setting","appid":{appid},"account":{account},"app":{app}}}"#
            ),
        )?;
        if !cloud_allowed(account, app) {
            return Self::finish(out, appid, &job, "cloud_disabled", None);
        }
        if kind == JobKind::Launch {
            // The local side, before anything comes down from Steam Cloud.
            self.saves.export(out, appid, "launch")?;
        }
        if let CloudCommand::Resolve(_, local) = command {
            let accepted = self.storage.resolve(appid, local);
            json(
                out,
                &format!(
                    r#"{{"event":"cloud_call","call":"ResolveSyncConflict","appid":{appid},"side":"{}","accepted":{accepted}}}"#,
                    if local { "local" } else { "cloud" }
                ),
            )?;
            if !accepted {
                return Self::finish(out, appid, &job, "resolve_refused", None);
            }
        }
        for &call in first_calls(kind) {
            self.storage.call(call, appid);
            Self::call_event(out, call.name(), appid)?;
        }
        self.jobs.insert(appid, job);
        Ok(())
    }
    fn tick(&mut self, out: &mut File) -> Result<(), String> {
        let now = Instant::now();
        let mut done = Vec::new();
        for (&appid, job) in self.jobs.iter_mut() {
            if now < job.next_poll {
                continue;
            }
            job.next_poll = now + POLL_INTERVAL;
            let in_progress = self.storage.in_progress(appid);
            let state = self.storage.state(appid);
            if job.reported != Some((state, in_progress)) {
                json(
                    out,
                    &format!(
                        r#"{{"event":"sync_state","appid":{appid},"state":{state},"name":"{}","in_progress":{in_progress}}}"#,
                        sync_state_name(state)
                    ),
                )?;
                job.reported = Some((state, in_progress));
            }
            let limit = match job.kind {
                JobKind::Launch => self.launch_timeout,
                JobKind::Exit | JobKind::Sync | JobKind::Resolve => JOB_TIMEOUT,
            };
            if now.duration_since(job.started) > limit {
                Self::finish(out, appid, job, "timeout", Some(state))?;
                done.push(appid);
                continue;
            }
            let busy = in_progress || state == 3;
            match job.awaiting_start_until {
                Some(_) if busy => job.awaiting_start_until = None,
                Some(until) if now < until => continue,
                _ => job.awaiting_start_until = None,
            }
            match next_step(job.kind, state, in_progress, job.progress) {
                SyncStep::Wait => {}
                SyncStep::Evaluate => {
                    self.storage.evaluate(appid);
                    job.progress.evaluations += 1;
                    job.awaiting_start_until = Some(now + START_GRACE);
                    Self::call_event(out, "EvaluateRemoteStorageSyncState", appid)?;
                }
                SyncStep::DownloadForLaunch => {
                    let accepted = self.storage.download_for_launch(appid);
                    job.progress.downloads += 1;
                    job.awaiting_start_until = Some(now + START_GRACE);
                    json(
                        out,
                        &format!(
                            r#"{{"event":"cloud_call","call":"SynchronizeApp","appid":{appid},"direction":"download","autocloud_launch":true,"accepted":{accepted}}}"#
                        ),
                    )?;
                    if !accepted {
                        // SynchronizeApp refuses when the app has no cloud quota.
                        Self::finish(out, appid, job, "download_not_started", Some(state))?;
                        done.push(appid);
                    }
                }
                SyncStep::LaunchPass(result) => {
                    for call in AUTOCLOUD_LAUNCH_PASS {
                        self.storage.call(call, appid);
                        Self::call_event(out, call.name(), appid)?;
                    }
                    job.progress.launch_pass = Some(result);
                    job.awaiting_start_until = Some(now + START_GRACE);
                }
                SyncStep::Upload => {
                    let accepted = self.storage.upload(appid);
                    job.progress.uploads += 1;
                    job.awaiting_start_until = Some(now + START_GRACE);
                    json(
                        out,
                        &format!(
                            r#"{{"event":"cloud_call","call":"SynchronizeApp","appid":{appid},"direction":"upload","accepted":{accepted}}}"#
                        ),
                    )?;
                }
                SyncStep::Finish(result) => {
                    // Report what the engine exposes about a conflict; overwrite nothing.
                    if state == 7 {
                        let (found, local, remote) = self.storage.conflict_timestamps(appid);
                        json(
                            out,
                            &format!(
                                r#"{{"event":"sync_conflict","appid":{appid},"found":{found},"local_time":{local},"remote_time":{remote}}}"#
                            ),
                        )?;
                    }
                    Self::finish(out, appid, job, result, Some(state))?;
                    done.push(appid);
                }
            }
        }
        for appid in done {
            if let Some(job) = self.jobs.remove(&appid) {
                if job.kind == JobKind::Exit {
                    self.saves.export(out, appid, "exit")?;
                }
            }
        }
        Ok(())
    }
    fn stop(&mut self, out: &mut File) -> Result<(), String> {
        for (&appid, job) in &self.jobs {
            Self::finish(out, appid, job, "stopped", None)?;
        }
        let exits: Vec<u32> = self
            .jobs
            .iter()
            .filter(|(_, job)| job.kind == JobKind::Exit)
            .map(|(&appid, _)| appid)
            .collect();
        self.jobs.clear();
        for appid in exits {
            self.saves.export(out, appid, "exit")?;
        }
        Ok(())
    }
}

// v8: install and uninstall jobs.
// EAppState bits, with the engine's own names: the (value, name) table at
// 0x2ad1510 that the content log prints ("state changed : Fully Installed,").
// GetAppInstallState returns the record's flags (1 when bit 0 is set), the value
// the appmanifest loader reads from "StateFlags" (install-evidence.txt).
const STATE_UNINSTALLED: u32 = 0x1;
const STATE_UPDATE_REQUIRED: u32 = 0x2;
const STATE_FULLY_INSTALLED: u32 = 0x4;
const STATE_UPDATE_QUEUED: u32 = 0x8;
const STATE_UPDATE_RUNNING: u32 = 0x100;
const STATE_UPDATE_PAUSED: u32 = 0x200;
const STATE_UPDATE_STARTED: u32 = 0x400;
const STATE_UNINSTALLING: u32 = 0x800;
const STATE_BACKUP_RUNNING: u32 = 0x1000;
const STATE_MOVING_FOLDER: u32 = 0x8000;
const STATE_TERMINATING: u32 = 0x10000;
const STATE_PREFETCHING_INFO: u32 = 0x20000;
const STATE_NAMES: [(u32, &str); 20] = [
    (0x1, "Uninstalled"),
    (0x2, "Update Required"),
    (0x4, "Fully Installed"),
    (0x8, "Update Queued"),
    (0x10, "Update Optional"),
    (0x20, "Files Missing"),
    (0x40, "Shared Only"),
    (0x80, "Files Corrupt"),
    (0x100, "Update Running"),
    (0x200, "Update Paused"),
    (0x400, "Update Started"),
    (0x800, "Uninstalling"),
    (0x1000, "Backup Running"),
    (0x2000, "App Running"),
    (0x4000, "Component In Use"),
    (0x8000, "Moving Folder"),
    (0x10000, "Terminating"),
    (0x20000, "Prefetching Info"),
    (0x40000, "Peer Server"),
    (0x80000, "Updated Disabled by app"),
];
/// Bits that mean an update, uninstall, backup or move is required, queued or runs.
const STATE_BUSY: u32 = STATE_UPDATE_REQUIRED
    | STATE_UPDATE_QUEUED
    | STATE_UPDATE_RUNNING
    | STATE_UPDATE_PAUSED
    | STATE_UPDATE_STARTED
    | STATE_UNINSTALLING
    | STATE_BACKUP_RUNNING
    | STATE_MOVING_FOLDER
    | STATE_TERMINATING
    | STATE_PREFETCHING_INFO;
/// EAppUpdateError names, from the engine's table at 0x2ad1710 (InstallApp,
/// UninstallApp and UpdateResult values).
fn update_error_name(code: u32) -> &'static str {
    const NAMES: [&str; 40] = [
        "No Error",
        "Unspecified Error",
        "Paused",
        "Canceled",
        "Suspended",
        "No subscription",
        "No connection",
        "Connection timeout",
        "Missing decryption key",
        "Missing configuration",
        "Disk read failure",
        "Disk write failure",
        "Not enough disk space",
        "Corrupt game files",
        "Waiting for disk",
        "Invalid install path",
        "Application running",
        "Dependency failure",
        "Not installed",
        "Update required",
        "Still busy",
        "No connection to content servers",
        "Invalid application configuration",
        "Invalid content configuration",
        "Manifest unavailable",
        "Not released",
        "Region restricted",
        "Corrupt depot cache",
        "Missing executable",
        "Invalid platform",
        "Invalid file system",
        "Corrupt update files",
        "Download disabled",
        "Shared library locked",
        "Purchase pending",
        "Other session playing",
        "Corrupt download",
        "Corrupt disk",
        "Missing file permissions",
        "File locked",
    ];
    NAMES.get(code as usize).copied().unwrap_or("unknown")
}
fn state_names(state: u32) -> String {
    let names: Vec<String> = STATE_NAMES
        .iter()
        .filter(|(bit, _)| state & bit != 0)
        .map(|(_, name)| format!("\"{name}\""))
        .collect();
    format!("[{}]", names.join(","))
}
const DEFAULT_INSTALL_TIMEOUT: Duration = Duration::from_secs(3600);
const INSTALL_TIMEOUT_VARIABLE: &str = "KORRI_STEAM_INSTALL_SECONDS";
const INSTALL_TIMEOUT_MAX: u64 = 86400;
const APP_POLL_INTERVAL: Duration = Duration::from_secs(1);
// A progress event at most this often while only the byte counts move.
const APP_PROGRESS_INTERVAL: Duration = Duration::from_secs(2);
// A paused update with a nonzero UpdateResult this long ends the job.
const INSTALL_STALL_LIMIT: Duration = Duration::from_secs(20);
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
struct UpdateInfo {
    bytes_downloaded: u64,
    bytes_to_download: u64,
    bytes_staged: u64,
    bytes_to_stage: u64,
    update_result: u32,
}
fn parse_update_info(raw: &[u8; UPDATE_INFO_SIZE]) -> UpdateInfo {
    let u64_at = |at: usize| u64::from_le_bytes(raw[at..at + 8].try_into().unwrap());
    let u32_at = |at: usize| u32::from_le_bytes(raw[at..at + 4].try_into().unwrap());
    UpdateInfo {
        bytes_downloaded: u64_at(UPDATE_INFO_BYTES_DOWNLOADED),
        bytes_to_download: u64_at(UPDATE_INFO_BYTES_TO_DOWNLOAD),
        bytes_staged: u64_at(UPDATE_INFO_BYTES_STAGED),
        bytes_to_stage: u64_at(UPDATE_INFO_BYTES_TO_STAGE),
        update_result: u32_at(UPDATE_INFO_UPDATE_RESULT),
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AppStep {
    Wait,
    Finish(&'static str),
}
/// One decision for a running install or uninstall job, after its engine call.
/// `stalled_for`: how long the update has been paused with a nonzero UpdateResult.
fn app_step(
    command: AppCommand,
    state: u32,
    up_to_date: bool,
    stalled_for: Option<Duration>,
) -> AppStep {
    match command {
        AppCommand::Install(_) => {
            if state & STATE_FULLY_INSTALLED != 0 && state & STATE_BUSY == 0 && up_to_date {
                AppStep::Finish("installed")
            } else if stalled_for.is_some_and(|d| d >= INSTALL_STALL_LIMIT) {
                AppStep::Finish("install_failed")
            } else {
                AppStep::Wait
            }
        }
        AppCommand::Uninstall(_) => {
            if state & STATE_UNINSTALLED != 0 && state & STATE_BUSY == 0 {
                AppStep::Finish("uninstalled")
            } else {
                AppStep::Wait
            }
        }
    }
}
fn install_stalled(state: u32, info: UpdateInfo) -> bool {
    state & STATE_UPDATE_PAUSED != 0 && info.update_result != 0
}
struct AppManager {
    object: Object,
}
impl AppManager {
    // SAFETY for all methods: the object's vptr and these slots were checked
    // against the engine map when the object was obtained.
    fn install(&self, appid: u32) -> u32 {
        let call: InstallApp = unsafe { slot(self.object, INSTALL_APP.0) };
        unsafe { call(self.object, appid, DEFAULT_LIBRARY_FOLDER, false) }
    }
    fn uninstall(&self, appid: u32) -> u32 {
        let call: AppUpdateCall = unsafe { slot(self.object, UNINSTALL_APP.0) };
        unsafe { call(self.object, appid) }
    }
    fn state(&self, appid: u32) -> u32 {
        let call: AppUpdateCall = unsafe { slot(self.object, GET_APP_INSTALL_STATE.0) };
        unsafe { call(self.object, appid) }
    }
    fn update_info(&self, appid: u32) -> Option<UpdateInfo> {
        let call: GetUpdateInfo = unsafe { slot(self.object, GET_UPDATE_INFO.0) };
        let mut raw = [0u8; UPDATE_INFO_SIZE];
        unsafe { call(self.object, appid, raw.as_mut_ptr()) }.then(|| parse_update_info(&raw))
    }
    fn up_to_date(&self, appid: u32) -> bool {
        let call: AppQuery = unsafe { slot(self.object, IS_APP_UP_TO_DATE.0) };
        unsafe { call(self.object, appid) }
    }
    fn downloading_enabled(&self) -> bool {
        let call: BoolQuery = unsafe { slot(self.object, IS_DOWNLOADING_ENABLED.0) };
        unsafe { call(self.object) }
    }
    fn downloading_appid(&self) -> u32 {
        let call: U32Query = unsafe { slot(self.object, GET_DOWNLOADING_APP_ID.0) };
        unsafe { call(self.object) }
    }
    fn queue_length(&self) -> u32 {
        let call: U32Query = unsafe { slot(self.object, GET_NUM_APPS_IN_DOWNLOAD_QUEUE.0) };
        unsafe { call(self.object) }
    }
}
struct AppJob {
    command: AppCommand,
    started: Instant,
    next_poll: Instant,
    reported: Option<(u32, bool, Option<UpdateInfo>)>,
    reported_at: Instant,
    stalled_since: Option<Instant>,
}
struct Apps {
    manager: AppManager,
    jobs: BTreeMap<u32, AppJob>,
    timeout: Duration,
    /// Engine offline logon: no content server can be reached.
    offline: bool,
}
impl Apps {
    fn finish(
        out: &mut File,
        job: &AppJob,
        result: &str,
        state: Option<u32>,
    ) -> Result<(), String> {
        let state = state.map_or("null".to_string(), |s| s.to_string());
        json(
            out,
            &format!(
                r#"{{"event":"app_job_finished","appid":{},"kind":"{}","result":"{result}","state":{state},"seconds":{}}}"#,
                job.command.appid(),
                job.command.name(),
                job.started.elapsed().as_secs()
            ),
        )
    }
    fn start(&mut self, out: &mut File, command: AppCommand) -> Result<(), String> {
        let appid = command.appid();
        let now = Instant::now();
        if let Some(old) = self.jobs.remove(&appid) {
            Self::finish(out, &old, "superseded", None)?;
        }
        json(
            out,
            &format!(
                r#"{{"event":"app_job_started","appid":{appid},"kind":"{}"}}"#,
                command.name()
            ),
        )?;
        let job = AppJob {
            command,
            started: now,
            next_poll: now,
            reported: None,
            reported_at: now,
            stalled_since: None,
        };
        if self.offline {
            return Self::finish(out, &job, "offline", None);
        }
        let state = self.manager.state(appid);
        let up_to_date = self.manager.up_to_date(appid);
        json(
            out,
            &format!(
                r#"{{"event":"app_state","appid":{appid},"state":{state},"names":{},"up_to_date":{up_to_date},"downloading_enabled":{},"queue":{}}}"#,
                state_names(state),
                self.manager.downloading_enabled(),
                self.manager.queue_length()
            ),
        )?;
        let (call, result) = match command {
            AppCommand::Install(_) => {
                if app_step(command, state, up_to_date, None) == AppStep::Finish("installed") {
                    return Self::finish(out, &job, "already_installed", Some(state));
                }
                ("InstallApp", self.manager.install(appid))
            }
            AppCommand::Uninstall(_) => ("UninstallApp", self.manager.uninstall(appid)),
        };
        json(
            out,
            &format!(
                r#"{{"event":"app_call","call":"{call}","appid":{appid},"library_folder":{},"result":{result}}}"#,
                if call == "InstallApp" {
                    DEFAULT_LIBRARY_FOLDER.to_string()
                } else {
                    "null".into()
                }
            ),
        )?;
        match (command, result) {
            (_, APP_UPDATE_OK) => {}
            (AppCommand::Uninstall(_), APP_UPDATE_NOT_INSTALLED) => {
                return Self::finish(out, &job, "not_installed", Some(state));
            }
            (AppCommand::Install(_), _) => {
                return Self::finish(out, &job, "install_refused", Some(state));
            }
            (AppCommand::Uninstall(_), _) => {
                return Self::finish(out, &job, "uninstall_refused", Some(state));
            }
        }
        self.jobs.insert(appid, job);
        Ok(())
    }
    fn tick(&mut self, out: &mut File) -> Result<(), String> {
        let now = Instant::now();
        let mut done = Vec::new();
        for (&appid, job) in self.jobs.iter_mut() {
            if now < job.next_poll {
                continue;
            }
            job.next_poll = now + APP_POLL_INTERVAL;
            let state = self.manager.state(appid);
            let up_to_date = self.manager.up_to_date(appid);
            let info = self.manager.update_info(appid);
            let current = (state, up_to_date, info);
            let state_changed = job.reported.map(|(s, u, _)| (s, u)) != Some((state, up_to_date));
            let moved = job.reported != Some(current);
            if state_changed
                || (moved && now.duration_since(job.reported_at) >= APP_PROGRESS_INTERVAL)
            {
                let i = info.unwrap_or_default();
                json(
                    out,
                    &format!(
                        r#"{{"event":"app_progress","appid":{appid},"kind":"{}","state":{state},"names":{},"up_to_date":{up_to_date},"update_info":{},"bytes_downloaded":{},"bytes_to_download":{},"bytes_staged":{},"bytes_to_stage":{},"update_result":{},"update_result_name":"{}","downloading_appid":{},"queue":{},"seconds":{}}}"#,
                        job.command.name(),
                        state_names(state),
                        info.is_some(),
                        i.bytes_downloaded,
                        i.bytes_to_download,
                        i.bytes_staged,
                        i.bytes_to_stage,
                        i.update_result,
                        update_error_name(i.update_result),
                        self.manager.downloading_appid(),
                        self.manager.queue_length(),
                        job.started.elapsed().as_secs()
                    ),
                )?;
                job.reported = Some(current);
                job.reported_at = now;
            }
            if install_stalled(state, info.unwrap_or_default()) {
                job.stalled_since.get_or_insert(now);
            } else {
                job.stalled_since = None;
            }
            if now.duration_since(job.started) > self.timeout {
                Self::finish(out, job, "timeout", Some(state))?;
                done.push(appid);
                continue;
            }
            let stalled_for = job.stalled_since.map(|since| now.duration_since(since));
            if let AppStep::Finish(result) = app_step(job.command, state, up_to_date, stalled_for) {
                Self::finish(out, job, result, Some(state))?;
                done.push(appid);
            }
        }
        for appid in done {
            self.jobs.remove(&appid);
        }
        Ok(())
    }
    fn stop(&mut self, out: &mut File) -> Result<(), String> {
        for job in self.jobs.values() {
            Self::finish(out, job, "stopped", None)?;
        }
        self.jobs.clear();
        Ok(())
    }
}

struct Session {
    engine: Object,
    pipe: i32,
    handle: i32,
    user: Object,
}
impl Session {
    fn close(&mut self) -> Result<(), String> {
        // SAFETY: slots were checked before handles were acquired; release occurs once.
        unsafe {
            if !self.user.is_null() {
                let logoff: NoArgs = slot(self.user, USER_LOG_OFF.0);
                logoff(self.user);
                self.user = ptr::null_mut();
            }
            if self.handle > 0 {
                let release: ReleaseUser = slot(self.engine, ENGINE_RELEASE_USER.0);
                release(self.engine, self.pipe, self.handle);
                self.handle = 0;
            }
            if self.pipe > 0 {
                let release: ReleasePipe = slot(self.engine, ENGINE_RELEASE_STEAM_PIPE.0);
                let ok = release(self.engine, self.pipe);
                self.pipe = 0;
                if !ok {
                    return Err("BReleaseSteamPipe failed".into());
                }
            }
        }
        Ok(())
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        let _ = self.close();
    }
}

/// The engine file's sha256, lowercase hex.
fn file_sha256(path: &Path) -> Result<String, String> {
    use sha2::{Digest, Sha256};
    let mut file = File::open(path).map_err(|_| "cannot read the engine file".to_string())?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = file
            .read(&mut buf)
            .map_err(|_| "cannot read the engine file".to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}

/// The start check of the engine (contract of #518): no map, or an engine file
/// that is not the map's build, ends the host before the engine is loaded.
fn engine_check(
    present: bool,
    expected: &str,
    found: impl FnOnce() -> Result<String, String>,
) -> Result<(), (String, String)> {
    if !present {
        return Err((
            r#"{"event":"engine_map_missing"}"#.into(),
            "the host was built without an engine map".into(),
        ));
    }
    let found = found().map_err(|e| (String::new(), e))?;
    if found != expected {
        return Err((
            format!(r#"{{"event":"engine_mismatch","expected":"{expected}","found":"{found}"}}"#),
            "the engine file is not the build of the engine map".into(),
        ));
    }
    Ok(())
}

/// The account name of the engine's saved login, beside HOME. It is not a
/// secret (korrid shows it); the login itself stays in the engine's stores.
const ACCOUNT_FILE: &str = ".korri-steam-account";
const MAX_ACCOUNT_NAME: usize = 64;
fn read_account(path: &Path) -> Option<CString> {
    let bytes = std::fs::read(path).ok()?;
    let name = std::str::from_utf8(&bytes).ok()?.trim();
    (!name.is_empty() && name.len() <= MAX_ACCOUNT_NAME)
        .then(|| CString::new(name).ok())
        .flatten()
}
fn write_account(path: &Path, name: &CStr) -> Result<(), String> {
    let temporary = path.with_extension("tmp");
    let _ = std::fs::remove_file(&temporary);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temporary)
        .map_err(|_| "cannot write the account file")?;
    file.write_all(name.to_bytes())
        .and_then(|_| file.sync_all())
        .map_err(|_| "cannot write the account file")?;
    std::fs::rename(&temporary, path).map_err(|_| "cannot write the account file".into())
}
/// Why the host starts signed out. The account name and the login are never
/// part of it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SignedOutReason {
    /// No readable account name file beside HOME.
    NoAccountFile,
    /// The engine has no cached login for the saved name
    /// (BHasCachedCredentials is false).
    NoSavedLogin,
    /// SetAccountNameForCachedCredentialLogin failed or gave no SteamID.
    SelectFailed,
}
impl SignedOutReason {
    fn name(self) -> &'static str {
        match self {
            SignedOutReason::NoAccountFile => "no_account_file",
            SignedOutReason::NoSavedLogin => "no_saved_login",
            SignedOutReason::SelectFailed => "select_failed",
        }
    }
}
/// The saved login to start with: the account name and its SteamID, or why
/// there is none. `cached` asks the engine for a cached login; `select`
/// selects the account and returns its SteamID (0 on failure).
fn start_login(
    account: Option<CString>,
    cached: impl FnOnce(&CStr) -> bool,
    select: impl FnOnce(&CStr) -> u64,
) -> Result<(CString, u64), SignedOutReason> {
    let name = account.ok_or(SignedOutReason::NoAccountFile)?;
    if !cached(&name) {
        return Err(SignedOutReason::NoSavedLogin);
    }
    let id = select(&name);
    if id == 0 || id as u32 == 0 {
        return Err(SignedOutReason::SelectFailed);
    }
    Ok((name, id))
}
/// After a QR sign-in the engine saves the login in two of its stores:
/// `local.vdf` (ConnectCache) at SetLoginToken, and `config/config.vdf` (store
/// "install") about 0.5 s after the logon (spike results/qr, run 3: 23:48:08.38
/// and 23:48:08.90). A host that stops between the two leaves a login that a
/// new process cannot select: on the Mini the QR job got `shutdown` right after
/// `signed_in`, config.vdf kept its old time and the next host started signed
/// out. So after a QR sign-in the host reports `signed_in`, and stops, only
/// once the engine has written config.vdf, or after LOGIN_SAVE_TIMEOUT.
/// The host only looks at the files' times; it never reads them.
const LOGIN_SAVE_TIMEOUT: Duration = Duration::from_secs(30);
/// The engine may flush the store more than once; let the last write land.
const LOGIN_SAVE_SETTLE: Duration = Duration::from_secs(1);
const INSTALL_STORE: &str = "config/config.vdf";
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct LoginSave {
    since: Instant,
    /// config.vdf's time when the token was handed over (None: no file).
    baseline: Option<std::time::SystemTime>,
    changed_at: Option<Instant>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SaveStep {
    Wait,
    Saved,
    Unconfirmed,
}
fn file_time(path: &Path) -> Option<std::time::SystemTime> {
    std::fs::metadata(path).and_then(|m| m.modified()).ok()
}
/// `install_store`: config.vdf's time now; `login_store`: local.vdf exists.
fn login_save_step(
    save: &mut LoginSave,
    now: Instant,
    install_store: Option<std::time::SystemTime>,
    login_store: bool,
) -> SaveStep {
    if login_store && install_store.is_some() && install_store != save.baseline {
        let at = *save.changed_at.get_or_insert(now);
        if now.duration_since(at) >= LOGIN_SAVE_SETTLE {
            return SaveStep::Saved;
        }
    }
    if now.duration_since(save.since) >= LOGIN_SAVE_TIMEOUT {
        SaveStep::Unconfirmed
    } else {
        SaveStep::Wait
    }
}
/// The engine's own store that holds its saved login (ConnectCache, spike
/// results/qr: written at SetLoginToken). Removed unread at `signout`.
const LOGIN_STORE: &str = "local.vdf";

/// The engine logs on with an EResult that says Steam no longer accepts this
/// client's protocol: k_EResultInvalidProtocolVer.
const ERESULT_INVALID_PROTOCOL_VERSION: i32 = 7;
/// SteamServerConnectFailure_t (callback 103) starts with its EResult.
const CALLBACK_CONNECT_FAILURE: i32 = 103;
fn refused_engine(eresult: i32) -> bool {
    eresult == ERESULT_INVALID_PROTOCOL_VERSION
}

const DEFAULT_QR_TIMEOUT: Duration = Duration::from_secs(600);
const QR_TIMEOUT_VARIABLE: &str = "KORRI_STEAM_QR_SECONDS";
const QR_TIMEOUT_MAX: u64 = 1800;
/// The name the Steam mobile app shows for this device.
const DEVICE_NAME_VARIABLE: &str = "KORRI_STEAM_DEVICE_NAME";
const MAX_SUBSCRIBED_APPS: usize = 1 << 16;
// After `signout`, LogOff gets this long to reach logon state 0.
const SIGNOUT_TIMEOUT: Duration = Duration::from_secs(5);

/// From the QR thread to the main loop.
enum QrMessage {
    Line(String),
    Challenge { url: String, first: bool },
    Done(Result<qr::Approved, qr::Failure>),
}
fn spawn_qr(
    device_name: String,
    limit: Duration,
    cancel: std::sync::Arc<AtomicBool>,
) -> mpsc::Receiver<QrMessage> {
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let stop = || cancel.load(Ordering::Relaxed);
        let mut report = |report: qr::Report| {
            let message = match report {
                qr::Report::Line(line) => QrMessage::Line(line.to_string()),
                qr::Report::Challenge { url, first } => QrMessage::Challenge {
                    url: url.to_string(),
                    first,
                },
            };
            sender
                .send(message)
                .map_err(|_| "main loop gone".to_string())
        };
        let result = qr::sign_in(&device_name, limit, &stop, &mut report);
        let _ = sender.send(QrMessage::Done(result));
    });
    receiver
}

/// list-apps: the account's licences (IClientUser::GetSubscribedApps), named
/// and typed from the engine's appinfo cache. Only games are reported.
/// `owned`: licensed without free licences; `free`: the rest.
/// Device proof: right after `signed_in` GetSubscribedApps returned no app at
/// all; Steam delivers the account's licences some seconds after the logon.
/// So list-apps first waits until the licence count is non-zero and has not
/// changed for LICENCE_SETTLE, at most LICENCE_TIMEOUT (an account with no
/// licences then lists nothing). Then, if some licensed apps have no record in
/// the engine's appinfo cache on disk, it waits once for the engine to write
/// appinfo.vdf again (APPINFO_SETTLE after the write), at most APPINFO_TIMEOUT.
const LICENCE_SETTLE: Duration = Duration::from_secs(3);
const LICENCE_TIMEOUT: Duration = Duration::from_secs(45);
const LICENCE_POLL: Duration = Duration::from_millis(500);
const APPINFO_SETTLE: Duration = Duration::from_secs(1);
const APPINFO_TIMEOUT: Duration = Duration::from_secs(30);
#[derive(Debug, Clone, PartialEq, Eq)]
enum ListWait {
    Licences {
        since: Instant,
        last: Option<usize>,
        stable_since: Instant,
    },
    Appinfo {
        since: Instant,
        baseline: Option<std::time::SystemTime>,
        changed_at: Option<Instant>,
    },
}
impl ListWait {
    fn new(now: Instant) -> Self {
        ListWait::Licences {
            since: now,
            last: None,
            stable_since: now,
        }
    }
}
/// One poll of the licence wait: true when the licences have settled or the
/// wait is over.
fn licences_settled(wait: &mut ListWait, now: Instant, count: usize) -> bool {
    let ListWait::Licences {
        since,
        last,
        stable_since,
    } = wait
    else {
        return true;
    };
    if *last != Some(count) {
        *last = Some(count);
        *stable_since = now;
    }
    (count > 0 && now.duration_since(*stable_since) >= LICENCE_SETTLE)
        || now.duration_since(*since) >= LICENCE_TIMEOUT
}
/// One poll of the appinfo wait: true when appinfo.vdf was written again and
/// settled, or the wait is over.
fn appinfo_written(
    wait: &mut ListWait,
    now: Instant,
    current: Option<std::time::SystemTime>,
) -> bool {
    let ListWait::Appinfo {
        since,
        baseline,
        changed_at,
    } = wait
    else {
        return true;
    };
    if current.is_some() && current != *baseline {
        let at = *changed_at.get_or_insert(now);
        if now.duration_since(at) >= APPINFO_SETTLE {
            return true;
        }
    }
    now.duration_since(*since) >= APPINFO_TIMEOUT
}
/// Licensed apps with no record in the appinfo cache on disk.
fn apps_without_appinfo(apps: &[u32], steam: &Path) -> usize {
    let known = std::fs::read(steam.join("appcache/appinfo.vdf"))
        .map_err(|_| "no appinfo.vdf".to_string())
        .and_then(|bytes| appinfo::read(&bytes))
        .unwrap_or_default();
    apps.iter()
        .filter(|appid| !known.contains_key(appid))
        .count()
}

fn list_apps(
    out: &mut File,
    subscribed: &dyn Fn(bool) -> Vec<u32>,
    steam: &Path,
) -> Result<(), String> {
    let owned: BTreeSet<u32> = subscribed(false).into_iter().collect();
    let all: BTreeSet<u32> = subscribed(true)
        .into_iter()
        .chain(owned.iter().copied())
        .collect();
    let apps = std::fs::read(steam.join("appcache/appinfo.vdf"))
        .map_err(|_| "no appinfo.vdf".to_string())
        .and_then(|bytes| appinfo::read(&bytes))
        .unwrap_or_default();
    let (mut no_appinfo, mut not_game) = (0, 0);
    for appid in all {
        let Some(app) = apps.get(&appid) else {
            no_appinfo += 1;
            continue;
        };
        match appinfo::name_and_type(app) {
            (Some(name), Some(kind)) if kind.eq_ignore_ascii_case("game") => json(
                out,
                &format!(
                    r#"{{"event":"app","appid":{appid},"name":{},"source":"{}"}}"#,
                    json_string(name.trim()),
                    if owned.contains(&appid) {
                        "owned"
                    } else {
                        "free"
                    }
                ),
            )?,
            _ => not_game += 1,
        }
    }
    json(
        out,
        &format!(r#"{{"event":"apps_skipped","no_appinfo":{no_appinfo},"not_game":{not_game}}}"#),
    )?;
    json(out, r#"{"event":"apps_done"}"#)
}

fn run(out: &mut File) -> Result<(), String> {
    let args = parse_args(env::args_os().skip(1).collect())?;
    let library = args
        .library
        .clone()
        .or_else(|| env::var_os("KORRI_STEAMCLIENT"))
        .ok_or("supply steamclient.so path as the sole argument or KORRI_STEAMCLIENT")?;
    let library = PathBuf::from(library);
    if !library.is_absolute() {
        return Err("steamclient.so path must be absolute".into());
    }
    if let Err((event, error)) =
        engine_check(ENGINE_MAP_PRESENT, ENGINE_SHA256, || file_sha256(&library))
    {
        if !event.is_empty() {
            json(out, &event)?;
        }
        return Err(error);
    }
    let channel = match &args.commands {
        CommandSource::Fifo(path) => {
            if !path.is_absolute() {
                return Err("--commands must name a FIFO by absolute path".into());
            }
            make_fifo(path)?;
            path.parent().map(Path::to_path_buf)
        }
        CommandSource::Stdin => None,
    };
    for path in [&args.session_lock, &args.host_lock].into_iter().flatten() {
        if !path.is_absolute() {
            return Err("--session-lock and --host-lock need an absolute path".into());
        }
    }
    // A value that is not UTF-8 reads as "" and is refused.
    let seconds_variable = |variable: &str, default: Duration, max: u64| {
        let value =
            env::var_os(variable).map(|v| v.to_str().map(str::to_owned).unwrap_or_default());
        parse_seconds(variable, value.as_deref(), default, max)
    };
    let launch_timeout = seconds_variable(
        LAUNCH_TIMEOUT_VARIABLE,
        DEFAULT_LAUNCH_TIMEOUT,
        LAUNCH_TIMEOUT_MAX,
    )?;
    let logon_timeout = seconds_variable(
        LOGON_TIMEOUT_VARIABLE,
        DEFAULT_LOGON_TIMEOUT,
        LOGON_TIMEOUT_MAX,
    )?;
    let stop_grace = seconds_variable(STOP_GRACE_VARIABLE, DEFAULT_STOP_GRACE, STOP_GRACE_MAX)?;
    let idle_timeout = seconds_variable(
        IDLE_TIMEOUT_VARIABLE,
        DEFAULT_IDLE_TIMEOUT,
        IDLE_TIMEOUT_MAX,
    )?;
    let install_timeout = seconds_variable(
        INSTALL_TIMEOUT_VARIABLE,
        DEFAULT_INSTALL_TIMEOUT,
        INSTALL_TIMEOUT_MAX,
    )?;
    let qr_timeout = seconds_variable(QR_TIMEOUT_VARIABLE, DEFAULT_QR_TIMEOUT, QR_TIMEOUT_MAX)?;
    let device_name = env::var(DEVICE_NAME_VARIABLE)
        .ok()
        .filter(|n| !n.trim().is_empty() && n.len() <= 64)
        .unwrap_or_else(|| "Korri".into());
    let home = PathBuf::from(env::var_os("HOME").ok_or("HOME is required")?);
    if !home.is_absolute() {
        return Err("HOME must be absolute".into());
    }
    let steam = home
        .join(".steam/steam")
        .canonicalize()
        .map_err(|_| "HOME/.steam/steam must resolve to the person's Steam engine folder")?;
    env::set_current_dir(&steam).map_err(|_| "cannot enter the Steam engine folder")?;
    if env::var_os("SteamAppId").is_some() || env::var_os("SteamGameId").is_some() {
        return Err(
            "unset SteamAppId and SteamGameId for the host process; set them only for the game"
                .into(),
        );
    }
    let account_file = home.join(ACCOUNT_FILE);
    let library = cstring(library.as_os_str().as_bytes(), "library path")?;
    let executable = cstring(
        steam.join("steam").as_os_str().as_bytes(),
        "Steam executable path",
    )?;
    let mut argv = [executable.as_ptr() as *mut c_char, ptr::null_mut()];
    // Held until the process exits (the descriptor is never closed before then).
    let _host_lock = match &args.host_lock {
        Some(path) => Some(take_host_lock(path, HOST_LOCK_WAIT)?),
        None => None,
    };
    let session_lock = match &args.session_lock {
        Some(path) => Some((open_lock(path)?, path.clone())),
        None => None,
    };
    json(
        out,
        &format!(
            r#"{{"event":"mode","mode":"{}","engine_client_version":"{ENGINE_CLIENT_VERSION}"}}"#,
            if session_lock.is_some() {
                "session"
            } else {
                "job"
            }
        ),
    )?;
    install_signals()?;
    json(out, r#"{"event":"phase","phase":"dlopen"}"#)?;
    // Valve's diagnostic streams are not forwarded. This prevents unstructured
    // stdout and accidental credential output from the engine. We never read them.
    let null = OpenOptions::new()
        .write(true)
        .open("/dev/null")
        .map_err(|_| "cannot open /dev/null")?;
    // SAFETY: owned output descriptors remain separate from redirected fd 1 and 2.
    if unsafe { dup2(null.as_raw_fd(), 1) } < 0 || unsafe { dup2(null.as_raw_fd(), 2) } < 0 {
        return Err("cannot suppress engine diagnostic streams".into());
    }
    let mut forget_login = false;
    // SAFETY: FFI declarations implement Linux C ABI. The library stays loaded
    // until process exit, including after Session cleanup; no dlclose race.
    unsafe {
        let lib = dlopen(library.as_ptr(), 2 | 0x100); // RTLD_NOW | RTLD_GLOBAL
        if lib.is_null() {
            let error = dlerror();
            return Err(if error.is_null() {
                "dlopen failed".into()
            } else {
                format!("dlopen failed: {}", CStr::from_ptr(error).to_string_lossy())
            });
        }
        let create = dlsym(lib, c"CreateInterface".as_ptr());
        if create.is_null() {
            return Err("CreateInterface export is missing".into());
        }
        let mut info = DlInfo {
            name: ptr::null(),
            base: ptr::null_mut(),
            symbol: ptr::null(),
            address: ptr::null_mut(),
        };
        if dladdr(create, &mut info) == 0
            || create as usize != info.base as usize + CREATE_INTERFACE_RVA
        {
            return Err(format!(
                "unsupported steamclient: CreateInterface RVA differs from the engine map (client {ENGINE_CLIENT_VERSION}, sha256 {ENGINE_SHA256})"
            ));
        }
        let base = info.base as usize;
        let factory: unsafe extern "C" fn(*const c_char, *mut i32) -> Object =
            std::mem::transmute(create);
        let mut status = -1;
        let engine = factory(CLIENT_ENGINE_VERSION.as_ptr(), &mut status);
        if status != 0 {
            return Err(format!("CreateInterface failed: status {status}"));
        }
        check_slots(
            engine,
            base,
            &[
                ENGINE_CREATE_STEAM_PIPE,
                ENGINE_RELEASE_STEAM_PIPE,
                ENGINE_CREATE_GLOBAL_USER,
                ENGINE_CONNECT_TO_GLOBAL_USER,
                ENGINE_RELEASE_USER,
                ENGINE_GET_USER,
                ENGINE_RUN_FRAME,
                ENGINE_GET_REMOTE_STORAGE,
                ENGINE_GET_APP_MANAGER,
                ENGINE_SET_COMMAND_LINE,
            ],
        )?;
        let command: CommandLine = slot(engine, ENGINE_SET_COMMAND_LINE.0);
        command(engine, 1, argv.as_mut_ptr());
        json(out, r#"{"event":"phase","phase":"create_global_user"}"#)?;
        let mut session = Session {
            engine,
            pipe: 0,
            handle: 0,
            user: ptr::null_mut(),
        };
        // CreateGlobalUser creates its own pipe and writes the output handle.
        // Calling CreateSteamPipe first would leak/replace that first pipe.
        let create_global: CreateGlobal = slot(engine, ENGINE_CREATE_GLOBAL_USER.0);
        session.handle = create_global(engine, &mut session.pipe);
        if session.handle <= 0 || session.pipe <= 0 {
            return Err("CreateGlobalUser failed (no user or pipe)".into());
        }
        install_signals()?;
        let get_user: GetUser = slot(engine, ENGINE_GET_USER.0);
        let user = get_user(engine, session.handle, session.pipe);
        // The returned interface may be the IPC proxy or the in-process CUser.
        if user.is_null() {
            return Err("GetIClientUser returned null".into());
        }
        let proxy = *user.cast::<usize>() == base + USER_PROXY_VTABLE;
        let local: [(usize, usize); USER_PROXY_SLOTS.len()];
        let expected = if proxy {
            &USER_PROXY_SLOTS[..]
        } else if let Some(rvas) = USER_LOCAL_RVAS {
            local = std::array::from_fn(|i| (USER_PROXY_SLOTS[i].0, rvas[i]));
            &local[..]
        } else {
            return Err(
                "GetIClientUser did not return the IPC proxy, and the engine map has no CUser table"
                    .into(),
            );
        };
        check_slots(user, base, expected)?;
        session.user = user;
        // The interface-set builder stores only the IPC proxy at the getter's field,
        // so accept only the proxy vtable; calls go through the engine's IPC thread.
        let get_storage: GetUser = slot(engine, ENGINE_GET_REMOTE_STORAGE.0);
        let storage = get_storage(engine, session.handle, session.pipe);
        if storage.is_null() || *storage.cast::<usize>() != base + REMOTE_STORAGE_PROXY_VTABLE {
            return Err("GetIClientRemoteStorage did not return the engine map's proxy".into());
        }
        check_slots(
            storage,
            base,
            &[
                IS_CLOUD_ENABLED_FOR_ACCOUNT,
                IS_CLOUD_ENABLED_FOR_APP,
                LOAD_LOCAL_FILE_INFO_CACHE,
                EVALUATE_SYNC_STATE,
                GET_SYNC_STATE,
                SYNCHRONIZE_APP,
                IS_APP_SYNC_IN_PROGRESS,
                RUN_AUTOCLOUD_ON_LAUNCH,
                RUN_AUTOCLOUD_ON_EXIT,
                GET_CONFLICTING_FILE_TIMESTAMPS,
                RESOLVE_SYNC_CONFLICT,
            ],
        )?;
        let mut cloud = Cloud {
            storage: RemoteStorage { object: storage },
            saves: SaveExports {
                dir: channel
                    .clone()
                    .unwrap_or_else(|| home.clone())
                    .join("saves"),
                steam: steam.clone(),
                home: home.clone(),
                steam_id: 0,
                sequence: 0,
            },
            jobs: BTreeMap::new(),
            launch_timeout,
            offline: false,
        };
        // The interface-set builder stores only the IPC proxy at +0x90.
        let get_app_manager: GetUser = slot(engine, ENGINE_GET_APP_MANAGER.0);
        let app_manager = get_app_manager(engine, session.handle, session.pipe);
        if app_manager.is_null() || *app_manager.cast::<usize>() != base + APP_MANAGER_PROXY_VTABLE
        {
            return Err("GetIClientAppManager did not return the engine map's proxy".into());
        }
        check_slots(
            app_manager,
            base,
            &[
                INSTALL_APP,
                UNINSTALL_APP,
                GET_APP_INSTALL_STATE,
                GET_UPDATE_INFO,
                IS_APP_UP_TO_DATE,
                IS_DOWNLOADING_ENABLED,
                GET_DOWNLOADING_APP_ID,
                GET_NUM_APPS_IN_DOWNLOAD_QUEUE,
            ],
        )?;
        let mut app_jobs = Apps {
            manager: AppManager {
                object: app_manager,
            },
            jobs: BTreeMap::new(),
            timeout: install_timeout,
            offline: false,
        };
        let callback_ptr = dlsym(lib, c"Steam_BGetCallback".as_ptr());
        let free_ptr = dlsym(lib, c"Steam_FreeLastCallback".as_ptr());
        if callback_ptr.is_null() || free_ptr.is_null() {
            return Err("callback exports missing".into());
        }
        let get_callback: GetCallback = std::mem::transmute(callback_ptr);
        let free_callback: FreeCallback = std::mem::transmute(free_ptr);
        let has_cached: CachedQuery = slot(user, USER_HAS_CACHED_CREDENTIALS.0);
        let select: SelectCached = slot(user, USER_SELECT_CACHED_ACCOUNT.0);
        let get_id: GetSteamId = slot(user, USER_STEAM_ID.0);
        let logon: LogOn = slot(user, USER_LOG_ON.0);
        let set_token: SetLoginToken = slot(user, USER_SET_LOGIN_TOKEN.0);
        let subscribed_call: SubscribedApps = slot(user, USER_GET_SUBSCRIBED_APPS.0);
        let subscribed = |include_free: bool| -> Vec<u32> {
            let mut list = vec![0u32; MAX_SUBSCRIBED_APPS];
            let total = subscribed_call(user, list.as_mut_ptr(), list.len() as u32, include_free);
            // The proxy copies min(total, max) entries (aa7e70..aa7e7c).
            list.truncate((total as usize).min(MAX_SUBSCRIBED_APPS));
            list
        };
        let (sender, commands) = mpsc::channel();
        spawn_command_reader(args.commands, sender);
        let mut pending: Vec<CloudCommand> = Vec::new();
        let mut app_pending: Vec<AppCommand> = Vec::new();
        let mut list_pending = false;
        let mut list_wait: Option<ListWait> = None;
        let mut next_list_poll = Instant::now();
        let frame: NoArgs = slot(engine, ENGINE_RUN_FRAME.0);
        let state: StateQuery = slot(user, USER_LOGON_STATE.0);
        let logged: BoolQuery = slot(user, USER_LOGGED_ON.0);
        let connected: BoolQuery = slot(user, USER_CONNECTED.0);
        let logoff: NoArgs = slot(user, USER_LOG_OFF.0);
        let can_logon_offline: CanLogonOffline = slot(user, USER_CAN_LOGON_OFFLINE.0);
        let logon_offline: LogOnOffline = slot(user, USER_LOGON_OFFLINE.0);
        // The saved login, when the engine still has one for the saved account name.
        let saved = start_login(
            read_account(&account_file),
            |name| has_cached(user, name.as_ptr()),
            |name| {
                if select(user, name.as_ptr(), false) {
                    get_id(user)
                } else {
                    0
                }
            },
        );
        let (mut account, mut id, signed_out) = match saved {
            Ok((name, steam_id)) => (Some(name), steam_id, None),
            Err(reason) => (None, 0, Some(reason)),
        };
        let mut phase = LogonPhase::SignedOut;
        // LogOn with the saved account, or report that nobody is signed in.
        let start_logon = |out: &mut File, id: u64| -> Result<LogonPhase, String> {
            let result = logon(user, id);
            json(out, r#"{"event":"phase","phase":"logon_started"}"#)?;
            if refused_engine(result) {
                json(
                    out,
                    &format!(r#"{{"event":"engine_refused","eresult":{result}}}"#),
                )?;
                return Err(format!(
                    "Steam refused this engine at sign-in (EResult {result})"
                ));
            }
            if result != ERESULT_OK {
                let reason = FallbackReason::LogOnRefused(result);
                json(
                    out,
                    &format!(r#"{{"event":"logon_fallback",{}}}"#, reason.json()),
                )?;
                return Ok(LogonPhase::LeavingNetwork {
                    deadline: Instant::now(),
                });
            }
            Ok(LogonPhase::Connecting {
                deadline: Instant::now() + logon_timeout,
            })
        };
        match signed_out {
            None => {
                cloud.saves.steam_id = id;
                phase = start_logon(out, id)?;
            }
            Some(reason) => json(
                out,
                &format!(r#"{{"event":"signed_out","reason":"{}"}}"#, reason.name()),
            )?,
        }
        let mut connect_failure: Option<i32> = None;
        let mut stop = StopControl::new(stop_grace);
        let mut previous = None;
        let mut account_setting_reported = false;
        let mut signed_in_reported = false;
        // After a QR sign-in: wait for the engine's login stores (LoginSave).
        let mut login_save: Option<LoginSave> = None;
        let mut stop_after_save = false;
        let mut next_offline_check = Instant::now();
        let mut offline_check_reported: Option<i32> = None;
        let qr_cancel = std::sync::Arc::new(AtomicBool::new(false));
        let mut qr: Option<mpsc::Receiver<QrMessage>> = None;
        let mut signing_out: Option<Instant> = None;
        // Inside Korri's session sandbox a stop kills the shim and the game at
        // once, so nobody is left to send `exited`. After STOP_IMPLIED_EXIT the
        // host treats every pending app as exited and runs its exit sync.
        let mut implied_exit: Option<(Instant, Vec<u32>)> = None;
        // Session lock probes and the idle clock.
        let mut next_session_probe = Instant::now();
        let mut session_held_reported: Option<bool> = None;
        let mut session_seen = false;
        let mut idle_since: Option<Instant> = None;
        let mut session_pids_reported = 0;
        'pump: loop {
            frame(engine);
            let now = Instant::now();
            // swap: a second SIGTERM sets the flag again and is seen as a repeat.
            if STOP.swap(false, Ordering::Relaxed) {
                match stop.signal(now) {
                    // A fresh login is saved first (LoginSave), at most 30 s.
                    StopAction::StopNow if login_save.is_some() => stop_after_save = true,
                    StopAction::StopNow => break 'pump,
                    StopAction::Wait {
                        pending: apps,
                        grace,
                    } => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"stop_requested","pending":{},"grace":{}}}"#,
                                appid_list(&apps),
                                grace.as_secs()
                            ),
                        )?;
                        implied_exit = Some((now + STOP_IMPLIED_EXIT, apps));
                    }
                    StopAction::Continue | StopAction::Expired { .. } => {}
                }
            }
            if implied_exit.as_ref().is_some_and(|(at, _)| now >= *at) {
                if let Some((_, apps)) = implied_exit.take() {
                    for appid in apps {
                        let command = CloudCommand::Exited(appid);
                        json(
                            out,
                            &format!(
                                r#"{{"event":"command","command":"exited","appid":{appid},"queued":false,"implied_by_stop":true}}"#
                            ),
                        )?;
                        stop.command(command);
                        pending.push(command);
                    }
                }
            }
            let offline = phase == LogonPhase::Offline;
            let current = (state(user), logged(user), connected(user), offline);
            if previous != Some(current) {
                json(
                    out,
                    &format!(
                        r#"{{"event":"logon_state","state":{},"logged_on":{},"connected":{},"offline":{}}}"#,
                        current.0, current.1, current.2, current.3
                    ),
                )?;
                previous = Some(current);
            }
            // `signout`: forget the login once LogOff reached state 0, then stop.
            if signing_out.is_some_and(|until| current.0 == 0 || now >= until) {
                forget_login = true;
                forget(&account_file, &steam);
                json(out, r#"{"event":"signed_out"}"#)?;
                break 'pump;
            }
            // The QR thread's reports, and its end.
            if let Some(receiver) = &qr {
                let mut finished = None;
                while let Ok(message) = receiver.try_recv() {
                    match message {
                        QrMessage::Line(line) => json(out, &line)?,
                        QrMessage::Challenge { url, first } => json(
                            out,
                            &format!(
                                r#"{{"event":"{}","challenge_url":{}}}"#,
                                if first { "qr_code" } else { "qr_refreshed" },
                                json_string(&url)
                            ),
                        )?,
                        QrMessage::Done(result) => finished = Some(result),
                    }
                }
                match finished {
                    None => {}
                    Some(Err(failure)) => {
                        qr = None;
                        phase = LogonPhase::SignedOut;
                        // The message names a method, an HTTP status or an EResult only.
                        json(
                            out,
                            &format!(
                                r#"{{"event":"qr_failure","message":{}}}"#,
                                json_string(&failure.message)
                            ),
                        )?;
                        json(
                            out,
                            &format!(
                                r#"{{"event":"signin_failed","reason":"{}"}}"#,
                                failure.reason
                            ),
                        )?;
                    }
                    Some(Ok(approved)) => {
                        qr = None;
                        let name = cstring(approved.account_name.as_bytes(), "account name")?;
                        // NUL-terminated copy for the engine; both copies are wiped on drop.
                        let mut token =
                            qr::Secret(Vec::with_capacity(approved.refresh_token.0.len() + 1));
                        token.0.extend_from_slice(&approved.refresh_token.0);
                        token.0.push(0);
                        drop(approved.refresh_token);
                        if token.0[..token.0.len() - 1].contains(&0) {
                            phase = LogonPhase::SignedOut;
                            json(out, r#"{"event":"signin_failed","reason":"steam_error"}"#)?;
                        } else {
                            set_token(user, token.0.as_ptr().cast(), name.as_ptr());
                            drop(token);
                            write_account(&account_file, &name)?;
                            json(out, r#"{"event":"login_token_set"}"#)?;
                            id = get_id(user);
                            if id == 0 || id as u32 == 0 {
                                phase = LogonPhase::SignedOut;
                                json(out, r#"{"event":"signin_failed","reason":"steam_error"}"#)?;
                            } else {
                                cloud.saves.steam_id = id;
                                account = Some(name);
                                connect_failure = None;
                                login_save = Some(LoginSave {
                                    since: Instant::now(),
                                    baseline: file_time(&steam.join(INSTALL_STORE)),
                                    changed_at: None,
                                });
                                phase = start_logon(out, id)?;
                            }
                        }
                    }
                }
            }
            match phase {
                LogonPhase::Connecting { deadline } => {
                    match connecting_step(now, deadline, current.1, connect_failure) {
                        ConnectStep::Wait => {}
                        ConnectStep::Online => phase = LogonPhase::Online,
                        ConnectStep::Fallback(reason) => {
                            json(
                                out,
                                &format!(r#"{{"event":"logon_fallback",{}}}"#, reason.json()),
                            )?;
                            // Stop the engine's connection attempts before going offline.
                            logoff(user);
                            phase = LogonPhase::LeavingNetwork {
                                deadline: now + LEAVE_NETWORK_TIMEOUT,
                            };
                        }
                    }
                }
                LogonPhase::LeavingNetwork { deadline }
                    if left_network(now, deadline, current.0) =>
                {
                    let Some(name) = &account else {
                        return Err("no account for offline logon".into());
                    };
                    // The offline calls validate the selected account's SteamID;
                    // select the account again if LogOff cleared it.
                    if get_id(user) != id
                        && (!select(user, name.as_ptr(), false) || get_id(user) != id)
                    {
                        cloud.stop(out)?;
                        return Err("could not select the cached account for offline logon".into());
                    }
                    let can = can_logon_offline(user);
                    json(
                        out,
                        &format!(
                            r#"{{"event":"offline_logon","call":"CanLogonOffline","result":{can}}}"#
                        ),
                    )?;
                    if can != ERESULT_OK {
                        cloud.stop(out)?;
                        return Err(format!(
                            "network logon failed and offline logon is not available (CanLogonOffline EResult {can})"
                        ));
                    }
                    let result = logon_offline(user, OFFLINE_MODE);
                    json(
                        out,
                        &format!(
                            r#"{{"event":"offline_logon","call":"LogOnOffline","result":{result}}}"#
                        ),
                    )?;
                    if result != ERESULT_OK {
                        cloud.stop(out)?;
                        return Err(format!("LogOnOffline failed with EResult {result}"));
                    }
                    cloud.offline = true;
                    app_jobs.offline = true;
                    phase = LogonPhase::Offline;
                }
                LogonPhase::LeavingNetwork { .. }
                | LogonPhase::Online
                | LogonPhase::Offline
                | LogonPhase::SignedOut
                | LogonPhase::Qr => {}
            }
            if !signed_in_reported && matches!(phase, LogonPhase::Online | LogonPhase::Offline) {
                let step = login_save.as_mut().map(|save| {
                    login_save_step(
                        save,
                        now,
                        file_time(&steam.join(INSTALL_STORE)),
                        steam.join(LOGIN_STORE).exists(),
                    )
                });
                let report = match step {
                    None => true,
                    Some(SaveStep::Wait) => false,
                    Some(step) => {
                        login_save = None;
                        json(
                            out,
                            &format!(
                                r#"{{"event":"login_saved","confirmed":{}}}"#,
                                step == SaveStep::Saved
                            ),
                        )?;
                        true
                    }
                };
                if let Some(name) = account.as_ref().filter(|_| report) {
                    signed_in_reported = true;
                    json(
                        out,
                        &format!(
                            r#"{{"event":"signed_in","account_name":{}}}"#,
                            json_string(&name.to_string_lossy())
                        ),
                    )?;
                }
            }
            if stop_after_save && login_save.is_none() {
                break 'pump;
            }
            let ready = session_ready(phase, current.1);
            while let Ok(received) = commands.try_recv() {
                match received {
                    Ok(Command::Shutdown) if login_save.is_some() => {
                        json(
                            out,
                            r#"{"event":"command","command":"shutdown","deferred":"login_save"}"#,
                        )?;
                        stop_after_save = true;
                    }
                    Ok(Command::Shutdown) => {
                        json(out, r#"{"event":"command","command":"shutdown"}"#)?;
                        break 'pump;
                    }
                    Ok(Command::Refused(refusal)) => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"launch_refused","reason":"{}","message":{}}}"#,
                                refusal.name(),
                                json_string(refusal.message())
                            ),
                        )?;
                    }
                    Ok(Command::SigninQr) => {
                        json(out, r#"{"event":"command","command":"signin-qr"}"#)?;
                        match phase {
                            LogonPhase::SignedOut if signing_out.is_none() => {
                                qr_cancel.store(false, Ordering::Relaxed);
                                qr = Some(spawn_qr(
                                    device_name.clone(),
                                    qr_timeout,
                                    qr_cancel.clone(),
                                ));
                                phase = LogonPhase::Qr;
                            }
                            LogonPhase::Qr => {
                                json(out, r#"{"event":"signin_failed","reason":"in_progress"}"#)?
                            }
                            _ => json(
                                out,
                                r#"{"event":"signin_failed","reason":"already_signed_in"}"#,
                            )?,
                        }
                    }
                    Ok(Command::Signout) => {
                        json(out, r#"{"event":"command","command":"signout"}"#)?;
                        qr_cancel.store(true, Ordering::Relaxed);
                        if matches!(phase, LogonPhase::SignedOut | LogonPhase::Qr) {
                            signing_out = Some(now);
                        } else {
                            logoff(user);
                            signing_out = Some(now + SIGNOUT_TIMEOUT);
                        }
                    }
                    Ok(Command::ListApps) => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"command","command":"list-apps","queued":{}}}"#,
                                !ready
                            ),
                        )?;
                        list_pending = true;
                    }
                    Ok(Command::App(command)) => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"command","command":"{}","appid":{},"queued":{}}}"#,
                                command.name(),
                                command.appid(),
                                !ready
                            ),
                        )?;
                        app_pending.push(command);
                    }
                    Ok(Command::Cloud(command)) => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"command","command":"{}","appid":{},"queued":{}}}"#,
                                command.name(),
                                command.appid(),
                                !ready
                            ),
                        )?;
                        stop.command(command);
                        pending.push(command);
                    }
                    Err(error) => json(
                        out,
                        &format!(r#"{{"event":"command_error","error":"{}"}}"#, error.name()),
                    )?,
                }
            }
            // Engine calls need a signed-in user or the offline session; keep commands until then.
            if ready && signing_out.is_none() {
                if phase == LogonPhase::Online {
                    if !account_setting_reported {
                        let account = cloud.storage.account_cloud_enabled();
                        json(
                            out,
                            &format!(r#"{{"event":"cloud_setting","account":{account}}}"#),
                        )?;
                        account_setting_reported = true;
                    }
                    // Would an offline logon work later? Read-only check; reported on change.
                    if now >= next_offline_check {
                        next_offline_check = now + OFFLINE_CHECK_INTERVAL;
                        let result = can_logon_offline(user);
                        if offline_check_reported != Some(result) {
                            json(
                                out,
                                &format!(r#"{{"event":"offline_logon_check","result":{result}}}"#),
                            )?;
                            offline_check_reported = Some(result);
                        }
                    }
                }
                if list_pending && now >= next_list_poll {
                    next_list_poll = now + LICENCE_POLL;
                    let wait = list_wait.get_or_insert_with(|| ListWait::new(now));
                    let mut ready = false;
                    match wait {
                        ListWait::Licences { since, .. } => {
                            let since = *since;
                            let all = subscribed(true);
                            if licences_settled(wait, now, all.len()) {
                                json(
                                    out,
                                    &format!(
                                        r#"{{"event":"licences","count":{},"seconds":{:.1}}}"#,
                                        all.len(),
                                        now.duration_since(since).as_secs_f32()
                                    ),
                                )?;
                                let missing = apps_without_appinfo(&all, &steam);
                                if missing == 0 {
                                    ready = true;
                                } else {
                                    json(
                                        out,
                                        &format!(
                                            r#"{{"event":"appinfo_wait","missing":{missing}}}"#
                                        ),
                                    )?;
                                    *wait = ListWait::Appinfo {
                                        since: now,
                                        baseline: file_time(&steam.join("appcache/appinfo.vdf")),
                                        changed_at: None,
                                    };
                                }
                            }
                        }
                        ListWait::Appinfo { .. } => {
                            ready = appinfo_written(
                                wait,
                                now,
                                file_time(&steam.join("appcache/appinfo.vdf")),
                            );
                        }
                    }
                    if ready {
                        list_pending = false;
                        list_wait = None;
                        list_apps(out, &subscribed, &steam)?;
                    }
                }
                for command in pending.drain(..) {
                    cloud.start(out, command)?;
                }
                cloud.tick(out)?;
                for command in app_pending.drain(..) {
                    app_jobs.start(out, command)?;
                }
                app_jobs.tick(out)?;
            }
            // Initialize user=0 to request every user's callback. Only the
            // EResult of a connection failure is read; no other payload.
            let mut message = Callback::default();
            for _ in 0..1024 {
                if !get_callback(session.pipe, &mut message) {
                    break;
                }
                let id = message.id;
                let eresult = (id == CALLBACK_CONNECT_FAILURE
                    && !message.data.is_null()
                    && message.size >= 4)
                    .then(|| message.data.cast::<i32>().read_unaligned());
                free_callback(session.pipe);
                json(out, &format!(r#"{{"event":"callback","id":{id}}}"#))?;
                if let Some(eresult) = eresult.filter(|e| refused_engine(*e)) {
                    json(
                        out,
                        &format!(r#"{{"event":"engine_refused","eresult":{eresult}}}"#),
                    )?;
                    cloud.stop(out)?;
                    app_jobs.stop(out)?;
                    return Err(format!("Steam refused this engine (EResult {eresult})"));
                }
                // SteamUser public callback IDs (UserCommon.h + 2 and + 3); no
                // payload is accessed. While connecting they start the offline
                // fallback; later they are only reported (the engine reconnects).
                if matches!(id, 102 | 103) && matches!(phase, LogonPhase::Connecting { .. }) {
                    connect_failure.get_or_insert(id);
                }
                message = Callback::default();
            }
            let busy = !cloud.jobs.is_empty()
                || !pending.is_empty()
                || !app_jobs.jobs.is_empty()
                || !app_pending.is_empty()
                || list_pending
                || qr.is_some()
                || login_save.is_some()
                || matches!(
                    phase,
                    LogonPhase::Connecting { .. } | LogonPhase::LeavingNetwork { .. }
                );
            if now >= next_session_probe {
                next_session_probe = now + SESSION_PROBE_INTERVAL;
                // Job mode has no session lock: only the idle clock applies.
                let free = match &session_lock {
                    Some((lock, lock_path)) => {
                        let free = try_lock(lock);
                        // The cgroup that `kill` translates from: the lock holder's.
                        let mut cgroup = SESSION_CGROUP
                            .lock()
                            .map_err(|_| "session cgroup lock poisoned")?;
                        if free {
                            *cgroup = None;
                        } else if cgroup.is_none() {
                            let content = std::fs::read_to_string(lock_path).unwrap_or_default();
                            if let Some(found) = session_cgroup_from(&content) {
                                json(
                                    out,
                                    &format!(
                                        r#"{{"event":"session_cgroup","cgroup":{}}}"#,
                                        json_string(&found)
                                    ),
                                )?;
                                *cgroup = Some(found);
                            }
                        }
                        drop(cgroup);
                        if free {
                            unlock(lock);
                        }
                        free
                    }
                    None => true,
                };
                let translated: Vec<(i32, i32)> = SESSION_PIDS
                    .lock()
                    .map(|s| s.iter().copied().skip(session_pids_reported).collect())
                    .unwrap_or_default();
                for (session, host) in translated {
                    json(
                        out,
                        &format!(r#"{{"event":"session_pid","session":{session},"host":{host}}}"#),
                    )?;
                    session_pids_reported += 1;
                }
                if session_lock.is_some() && session_held_reported != Some(!free) {
                    json(
                        out,
                        &format!(r#"{{"event":"session_lock","held":{}}}"#, !free),
                    )?;
                    session_held_reported = Some(!free);
                }
                session_seen |= !free;
                let action = session_step(
                    &mut idle_since,
                    idle_timeout,
                    now,
                    !free,
                    session_seen,
                    stop.running(),
                    busy,
                );
                match action {
                    SessionAction::IdleStop => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"idle_stop","seconds":{}}}"#,
                                idle_timeout.as_secs()
                            ),
                        )?;
                        break 'pump;
                    }
                    SessionAction::Over => {
                        json(out, r#"{"event":"session_over"}"#)?;
                        break 'pump;
                    }
                    SessionAction::Ended { pending: apps } => {
                        json(
                            out,
                            &format!(
                                r#"{{"event":"session_ended","pending":{}}}"#,
                                appid_list(&apps)
                            ),
                        )?;
                        for appid in apps {
                            let command = CloudCommand::Exited(appid);
                            json(
                                out,
                                &format!(
                                    r#"{{"event":"command","command":"exited","appid":{appid},"queued":{},"implied_by_session_end":true}}"#,
                                    !ready
                                ),
                            )?;
                            stop.command(command);
                            pending.push(command);
                        }
                    }
                    SessionAction::Continue => {}
                }
            }
            match stop.poll(Instant::now(), busy) {
                StopAction::StopNow => break 'pump,
                StopAction::Expired { pending: apps } => {
                    json(
                        out,
                        &format!(
                            r#"{{"event":"stop_wait_expired","pending":{}}}"#,
                            appid_list(&apps)
                        ),
                    )?;
                    break 'pump;
                }
                StopAction::Continue | StopAction::Wait { .. } => {}
            }
            thread::sleep(Duration::from_millis(10));
        }
        qr_cancel.store(true, Ordering::Relaxed);
        cloud.stop(out)?;
        app_jobs.stop(out)?;
        session.close()?;
        if forget_login {
            // The engine may have flushed its store again while it logged off.
            forget(&account_file, &steam);
        }
        json(out, r#"{"event":"phase","phase":"stopped"}"#)?;
    }
    Ok(())
}

/// Removes the account name file and the engine's login store, unread.
fn forget(account_file: &Path, steam: &Path) {
    let _ = std::fs::remove_file(account_file);
    let _ = std::fs::remove_file(steam.join(LOGIN_STORE));
}

/// The command FIFO: made with mode 0660 when missing; an existing one is kept,
/// because a writer may already wait in open() on its inode.
fn make_fifo(path: &Path) -> Result<(), String> {
    match std::fs::symlink_metadata(path) {
        Ok(meta) if meta.file_type().is_fifo() => Ok(()),
        Ok(_) => Err("--commands names a file that is not a FIFO".into()),
        Err(_) => {
            let name = cstring(path.as_os_str().as_bytes(), "FIFO path")?;
            // SAFETY: mkfifo with a NUL-terminated path.
            if unsafe { mkfifo(name.as_ptr(), 0o660) } != 0 {
                return Err("cannot make the command FIFO".into());
            }
            Ok(())
        }
    }
}

fn main() {
    let mut errors = owned_fd(2).expect("cannot duplicate stderr");
    let result = owned_fd(1).and_then(|mut out| run(&mut out));
    let status = match result {
        Ok(()) => 0,
        Err(error) => {
            let _ = writeln!(errors, "korri-steam-host: {error}");
            1
        }
    };
    // v7: leave without exit handlers. The engine's threads keep running after
    // LogOff and release, and steamclient.so's static destructors (run by
    // exit()) let one of them fault: v6 and v7 hosts on the Mini repeatedly
    // ended with SIGSEGV in steamclient.so after "phase stopped" (coredumps of
    // 2026-11-17; the unit then shows "failed").
    // All output is already written: json() flushes each line, stderr is unbuffered.
    // SAFETY: _exit only ends the process.
    unsafe { _exit(status) }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cleanup_releases_once_in_order() {
        // The slot numbers come from the engine map; the empty map has none.
        if !ENGINE_MAP_PRESENT {
            return;
        }
        use std::sync::Mutex;
        static CALLS: Mutex<Vec<&str>> = Mutex::new(Vec::new());
        unsafe extern "C" fn logoff(_: Object) {
            CALLS.lock().unwrap().push("logoff");
        }
        unsafe extern "C" fn release_user(_: Object, pipe: i32, user: i32) {
            assert_eq!((pipe, user), (7, 8));
            CALLS.lock().unwrap().push("user");
        }
        unsafe extern "C" fn release_pipe(_: Object, pipe: i32) -> bool {
            assert_eq!(pipe, 7);
            CALLS.lock().unwrap().push("pipe");
            true
        }
        let mut engine_table = [0usize; 128];
        engine_table[ENGINE_RELEASE_STEAM_PIPE.0] = release_pipe as *const () as usize;
        engine_table[ENGINE_RELEASE_USER.0] = release_user as *const () as usize;
        let mut user_table = [0usize; 128];
        user_table[USER_LOG_OFF.0] = logoff as *const () as usize;
        let mut engine_ptr = engine_table.as_ptr();
        let mut user_ptr = user_table.as_ptr();
        let mut session = Session {
            engine: (&mut engine_ptr as *mut *const usize).cast(),
            user: (&mut user_ptr as *mut *const usize).cast(),
            pipe: 7,
            handle: 8,
        };
        session.close().unwrap();
        session.close().unwrap();
        drop(session);
        assert_eq!(*CALLS.lock().unwrap(), vec!["logoff", "user", "pipe"]);
    }
    #[test]
    fn callback_layout() {
        assert_eq!(std::mem::size_of::<Callback>(), 24);
        assert_eq!(std::mem::offset_of!(Callback, user), 0);
        assert_eq!(std::mem::offset_of!(Callback, id), 4);
        assert_eq!(std::mem::offset_of!(Callback, data), 8);
        assert_eq!(std::mem::offset_of!(Callback, size), 16);
    }
    #[test]
    fn embedded_nul_is_not_echoed() {
        assert_eq!(
            cstring(b"never-print-this\0", "account name").unwrap_err(),
            "account name contains a NUL byte"
        );
    }
    #[test]
    fn callback_payload_is_never_formatted() {
        let message = Callback {
            id: 101,
            data: 1usize as Object,
            ..Callback::default()
        };
        assert_eq!(
            format!(r#"{{"event":"callback","id":{}}}"#, message.id),
            r#"{"event":"callback","id":101}"#
        );
    }
    #[test]
    fn parse_command_accepts_the_four_verbs() {
        use CloudCommand::*;
        let cloud = |command| Ok(Some(Command::Cloud(command)));
        assert_eq!(parse_command("launched 584400"), cloud(Launched(584400)));
        assert_eq!(parse_command("exited 584400\n"), cloud(Exited(584400)));
        assert_eq!(parse_command("  sync\t7  \r\n"), cloud(Sync(7)));
        assert_eq!(parse_command("sync 4294967295"), cloud(Sync(u32::MAX)));
        assert_eq!(parse_command("shutdown"), Ok(Some(Command::Shutdown)));
        assert_eq!(parse_command(" shutdown \r\n"), Ok(Some(Command::Shutdown)));
    }
    #[test]
    fn parse_command_accepts_install_and_uninstall() {
        use AppCommand::*;
        assert_eq!(
            parse_command("install 78000"),
            Ok(Some(Command::App(Install(78000))))
        );
        assert_eq!(
            parse_command(" uninstall\t78000\r\n"),
            Ok(Some(Command::App(Uninstall(78000))))
        );
        assert_eq!(parse_command("install"), Err(CommandError::MissingAppId));
        assert_eq!(parse_command("install 0"), Err(CommandError::InvalidAppId));
        assert_eq!(
            parse_command("uninstall 1 2"),
            Err(CommandError::ExtraArguments)
        );
        assert_eq!(
            parse_command("INSTALL 5"),
            Err(CommandError::UnknownCommand)
        );
        assert_eq!(Install(5).name(), "install");
        assert_eq!(Uninstall(6).appid(), 6);
    }
    #[test]
    fn parse_command_ignores_blank_lines() {
        assert_eq!(parse_command(""), Ok(None));
        assert_eq!(parse_command(" \t\r\n"), Ok(None));
    }
    #[test]
    fn parse_command_rejects_bad_input() {
        use CommandError::*;
        assert_eq!(parse_command("upload 584400"), Err(UnknownCommand));
        assert_eq!(parse_command("SYNC 584400"), Err(UnknownCommand));
        assert_eq!(parse_command("sync"), Err(MissingAppId));
        assert_eq!(parse_command("sync 0"), Err(InvalidAppId));
        assert_eq!(parse_command("sync +5"), Err(InvalidAppId));
        assert_eq!(parse_command("sync -5"), Err(InvalidAppId));
        assert_eq!(parse_command("sync 0x10"), Err(InvalidAppId));
        assert_eq!(parse_command("sync 4294967296"), Err(InvalidAppId));
        assert_eq!(parse_command("sync 5 6"), Err(ExtraArguments));
        assert_eq!(parse_command("shutdown 584400"), Err(ExtraArguments));
        assert_eq!(parse_command("SHUTDOWN"), Err(UnknownCommand));
    }
    #[test]
    fn command_errors_never_echo_the_line() {
        let (sender, receiver) = mpsc::channel();
        let input = b"secret-looking-text 1\nsync 584400\n\n".to_vec();
        read_commands(&mut &input[..], &sender).unwrap();
        let got: Vec<_> = receiver.try_iter().collect();
        assert_eq!(
            got,
            vec![
                Err(CommandError::UnknownCommand),
                Ok(Command::Cloud(CloudCommand::Sync(584400)))
            ]
        );
        assert_eq!(CommandError::UnknownCommand.name(), "unknown_command");
    }
    #[test]
    fn read_commands_limits_line_length_and_resynchronizes() {
        let (sender, receiver) = mpsc::channel();
        let mut input = vec![b'x'; MAX_COMMAND_LINE + 50];
        input.extend_from_slice(b"\nexited 10\n\xff\xfe 1\n");
        read_commands(&mut &input[..], &sender).unwrap();
        let got: Vec<_> = receiver.try_iter().collect();
        assert_eq!(
            got,
            vec![
                Err(CommandError::LineTooLong),
                Ok(Command::Cloud(CloudCommand::Exited(10))),
                Err(CommandError::NotUtf8)
            ]
        );
    }
    #[test]
    fn read_commands_accepts_a_full_length_line_and_a_last_line_without_newline() {
        let (sender, receiver) = mpsc::channel();
        let mut input = b"sync 5".to_vec();
        input.resize(MAX_COMMAND_LINE, b' ');
        input.extend_from_slice(b"\nlaunched 3");
        read_commands(&mut &input[..], &sender).unwrap();
        assert_eq!(
            receiver.try_iter().collect::<Vec<_>>(),
            vec![
                Ok(Command::Cloud(CloudCommand::Sync(5))),
                Ok(Command::Cloud(CloudCommand::Launched(3)))
            ]
        );
    }
    #[test]
    fn parse_args_reads_commands_fifo_and_library() {
        let os = |v: &[&str]| v.iter().map(OsString::from).collect::<Vec<_>>();
        assert_eq!(
            parse_args(os(&[])),
            Ok(Args {
                library: None,
                commands: CommandSource::Stdin,
                session_lock: None,
                host_lock: None,
            })
        );
        assert_eq!(
            parse_args(os(&["--commands", "/run/x.fifo", "/a/steamclient.so"])),
            Ok(Args {
                library: Some("/a/steamclient.so".into()),
                commands: CommandSource::Fifo("/run/x.fifo".into()),
                session_lock: None,
                host_lock: None,
            })
        );
        assert_eq!(
            parse_args(os(&["/a/steamclient.so", "--commands", "/f"]))
                .unwrap()
                .library,
            Some("/a/steamclient.so".into())
        );
        assert_eq!(parse_args(os(&["--commands"])), Err(USAGE.into()));
        assert_eq!(
            parse_args(os(&["--commands", "/f", "--commands", "/g"])),
            Err(USAGE.into())
        );
        assert_eq!(parse_args(os(&["/a.so", "/b.so"])), Err(USAGE.into()));
        assert_eq!(parse_args(os(&["--verbose"])), Err(USAGE.into()));
    }
    #[test]
    fn parse_args_reads_the_session_and_host_locks() {
        let os = |v: &[&str]| v.iter().map(OsString::from).collect::<Vec<_>>();
        assert_eq!(
            parse_args(os(&[
                "--session-lock",
                "/s/session.lock",
                "--commands",
                "/s/cmd.fifo",
                "--host-lock",
                "/s/host.lock",
                "/a/steamclient.so",
            ])),
            Ok(Args {
                library: Some("/a/steamclient.so".into()),
                commands: CommandSource::Fifo("/s/cmd.fifo".into()),
                session_lock: Some("/s/session.lock".into()),
                host_lock: Some("/s/host.lock".into()),
            })
        );
        for bad in [
            &["--session-lock"][..],
            &["--host-lock"],
            &["--session-lock", "/a", "--session-lock", "/b"],
            &["--host-lock", "/a", "--host-lock", "/b"],
        ] {
            assert_eq!(parse_args(os(bad)), Err(USAGE.into()), "{bad:?}");
        }
    }
    const IDLE: Duration = Duration::from_secs(300);
    #[test]
    fn session_lock_free_with_a_running_app_ends_the_session() {
        let now = Instant::now();
        let mut idle = None;
        // The shim holds the lock while the game runs.
        assert_eq!(
            session_step(&mut idle, IDLE, now, true, false, vec![584400], false),
            SessionAction::Continue
        );
        // The shim was killed: implied `exited` for every running app, also
        // while that app's launch job still runs.
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, false, vec![400, 584400], true),
            SessionAction::Ended {
                pending: vec![400, 584400]
            }
        );
        assert_eq!(idle, None);
    }
    #[test]
    fn session_idle_stop_needs_a_free_lock_no_app_and_no_job_for_the_whole_timeout() {
        let now = Instant::now();
        let mut idle = None;
        // The exit job still runs: not idle.
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, false, vec![], true),
            SessionAction::Continue
        );
        assert_eq!(idle, None);
        let start = now + Duration::from_secs(1);
        assert_eq!(
            session_step(&mut idle, IDLE, start, false, false, vec![], false),
            SessionAction::Continue
        );
        assert_eq!(idle, Some(start));
        assert_eq!(
            session_step(
                &mut idle,
                IDLE,
                start + IDLE / 2,
                false,
                false,
                vec![],
                false
            ),
            SessionAction::Continue
        );
        // A new session takes the lock: the idle time starts again later.
        assert_eq!(
            session_step(
                &mut idle,
                IDLE,
                start + IDLE / 2,
                true,
                false,
                vec![],
                false
            ),
            SessionAction::Continue
        );
        assert_eq!(idle, None);
        let again = start + IDLE;
        assert_eq!(
            session_step(&mut idle, IDLE, again, false, false, vec![], false),
            SessionAction::Continue
        );
        assert_eq!(
            session_step(&mut idle, IDLE, again + IDLE, false, false, vec![], false),
            SessionAction::IdleStop
        );
    }
    #[test]
    fn idle_timeout_defaults_to_300_seconds() {
        let parse = |value| {
            parse_seconds(
                IDLE_TIMEOUT_VARIABLE,
                value,
                DEFAULT_IDLE_TIMEOUT,
                IDLE_TIMEOUT_MAX,
            )
        };
        assert_eq!(parse(None), Ok(Duration::from_secs(300)));
        assert_eq!(parse(Some("1")), Ok(Duration::from_secs(1)));
        assert_eq!(parse(Some("3600")), Ok(Duration::from_secs(3600)));
        for bad in ["", "0", "3601", "5m"] {
            assert!(parse(Some(bad)).is_err(), "{bad}");
        }
    }
    #[test]
    fn nspid_match_finds_the_host_pid_of_a_session_pid() {
        let status =
            "Name:\twine64-preloade\nTgid:\t135636\nPid:\t135636\nNSpid:\t135636\t459\nNSsid:\t1\n";
        assert_eq!(nspid_match(status, 459), Some(135636));
        assert_eq!(nspid_match(status, 135636), None);
        assert_eq!(nspid_match(status, 460), None);
        // A process of this namespace only (one entry) is never translated.
        assert_eq!(nspid_match("NSpid:\t459\n", 459), None);
        assert_eq!(nspid_match("Pid:\t459\n", 459), None);
        assert_eq!(nspid_match("NSpid:\t1\tx\n", 1), None);
    }
    #[test]
    fn session_cgroup_is_read_from_the_lock_file() {
        let unit =
            "/korri.slice/korri-games.slice/korri-game-3b5f66b2443d10168c042b1ee393d214.service";
        assert_eq!(session_cgroup_from(&format!("{unit}\n")), Some(unit.into()));
        for bad in [
            "",
            "\n",
            "/",
            "korri.slice/x.service",
            "/a/../b",
            "/a b",
            "/a\"b",
        ] {
            assert_eq!(session_cgroup_from(bad), None, "{bad:?}");
        }
    }
    #[test]
    fn kill_without_a_session_passes_the_pid_through() {
        // No session: kill(own pid, 0) is the plain system call.
        assert_eq!(kill(std::process::id() as c_int, 0), 0);
        assert_eq!(session_pid("/no.slice/none.service", 1), None);
        assert_eq!(session_pid("/", 0), None);
    }
    #[test]
    fn locks_see_another_holder_and_its_release() {
        let dir = env::temp_dir().join(format!("korri-steam-host-lock-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("session.lock");
        let shim = open_lock(&path).unwrap();
        assert!(try_lock(&shim));
        let host = open_lock(&path).unwrap();
        // Same file, another open file description: the shim's lock blocks it.
        assert!(!try_lock(&host));
        assert!(take_host_lock(&path, Duration::from_millis(200)).is_err());
        drop(shim);
        assert!(try_lock(&host));
        unlock(&host);
        let held = take_host_lock(&path, Duration::from_millis(200)).unwrap();
        assert!(!try_lock(&host));
        drop(held);
        std::fs::remove_dir_all(&dir).unwrap();
    }
    fn done(evaluations: u8, uploads: u8) -> Progress {
        Progress {
            evaluations,
            uploads,
            ..Progress::default()
        }
    }
    #[test]
    fn sync_job_evaluates_first_then_uploads_local_changes() {
        use JobKind::*;
        assert_eq!(next_step(Exit, 2, false, done(0, 0)), SyncStep::Evaluate);
        assert_eq!(next_step(Sync, 5, false, done(0, 0)), SyncStep::Evaluate);
        assert_eq!(next_step(Sync, 5, false, done(1, 0)), SyncStep::Upload);
        assert_eq!(
            next_step(Sync, 5, false, done(1, 2)),
            SyncStep::Finish("upload_incomplete")
        );
        assert_eq!(
            next_step(Sync, 2, false, done(1, 1)),
            SyncStep::Finish("synchronized")
        );
        assert_eq!(next_step(Sync, 8, false, done(1, 0)), SyncStep::Evaluate);
        assert_eq!(
            next_step(Sync, 1, false, done(2, 0)),
            SyncStep::Finish("evaluation_incomplete")
        );
    }
    #[test]
    fn sync_job_waits_while_the_engine_is_busy() {
        assert_eq!(
            next_step(JobKind::Sync, 3, false, done(1, 0)),
            SyncStep::Wait
        );
        assert_eq!(
            next_step(JobKind::Sync, 5, true, done(1, 0)),
            SyncStep::Wait
        );
        assert_eq!(
            next_step(JobKind::Launch, 2, true, done(0, 0)),
            SyncStep::Wait
        );
        assert_eq!(
            next_step(JobKind::Launch, 4, true, done(1, 0)),
            SyncStep::Wait
        );
    }
    #[test]
    fn sync_job_never_downloads_or_resolves_conflicts() {
        for (state, result) in [
            (4, "remote_changes_not_downloaded"),
            (6, "local_and_remote_changes_not_synced"),
            (7, "conflict_not_resolved"),
            (0, "no_sync_state"),
            (9, "unhandled_state"),
        ] {
            assert_eq!(
                next_step(JobKind::Sync, state, false, done(1, 0)),
                SyncStep::Finish(result)
            );
        }
    }
    #[test]
    fn launch_job_evaluates_then_downloads_remote_changes_with_the_launch_pass() {
        use JobKind::Launch;
        assert_eq!(next_step(Launch, 2, false, done(0, 0)), SyncStep::Evaluate);
        assert_eq!(next_step(Launch, 8, false, done(1, 0)), SyncStep::Evaluate);
        assert_eq!(
            next_step(Launch, 1, false, done(2, 0)),
            SyncStep::Finish("evaluation_incomplete")
        );
        for state in [4, 6] {
            assert_eq!(
                next_step(Launch, state, false, done(1, 0)),
                SyncStep::DownloadForLaunch
            );
        }
        assert_eq!((SYNC_DOWNLOAD, SYNC_FLAG_AUTOCLOUD_LAUNCH), (1, 2));
    }
    #[test]
    fn launch_job_reports_what_the_download_left() {
        use JobKind::Launch;
        let downloaded = Progress {
            downloads: 1,
            ..done(1, 0)
        };
        for (state, result) in [
            (2, "downloaded"),
            (5, "downloaded"),
            (7, "conflict"),
            (4, "download_incomplete"),
            (6, "download_incomplete"),
            (0, "no_sync_state"),
        ] {
            assert_eq!(
                next_step(Launch, state, false, downloaded),
                SyncStep::Finish(result)
            );
        }
    }
    #[test]
    fn launch_job_keeps_local_files_and_runs_only_the_launch_pass() {
        use JobKind::Launch;
        for (state, result) in [(2, "synchronized"), (5, "local_changes"), (7, "conflict")] {
            assert_eq!(
                next_step(Launch, state, false, done(1, 0)),
                SyncStep::LaunchPass(result)
            );
            let passed = Progress {
                launch_pass: Some(result),
                ..done(1, 0)
            };
            assert_eq!(
                next_step(Launch, state, false, passed),
                SyncStep::Finish(result)
            );
        }
        let passed = Progress {
            launch_pass: Some("synchronized"),
            ..done(1, 0)
        };
        assert_eq!(
            next_step(Launch, 7, false, passed),
            SyncStep::Finish("conflict")
        );
        assert_eq!(
            AUTOCLOUD_LAUNCH_PASS,
            [
                CloudCall::RunAutoCloudOnAppLaunch,
                CloudCall::LoadLocalFileInfoCache
            ]
        );
    }
    #[test]
    fn launch_timeout_defaults_to_120_seconds_and_rejects_bad_values() {
        let parse = |value| {
            parse_seconds(
                LAUNCH_TIMEOUT_VARIABLE,
                value,
                DEFAULT_LAUNCH_TIMEOUT,
                LAUNCH_TIMEOUT_MAX,
            )
        };
        assert_eq!(parse(None), Ok(Duration::from_secs(120)));
        assert_eq!(parse(Some("30")), Ok(Duration::from_secs(30)));
        assert_eq!(parse(Some("3600")), Ok(Duration::from_secs(3600)));
        for bad in ["", "0", "3601", "-1", "1.5", "120s"] {
            assert!(parse(Some(bad)).is_err(), "{bad}");
        }
        assert_eq!(
            parse(Some("0")).unwrap_err(),
            "KORRI_STEAM_LAUNCH_SYNC_SECONDS must be a whole number of seconds from 1 to 3600"
        );
    }
    #[test]
    fn stop_grace_defaults_to_45_seconds_and_stays_under_systemds_90() {
        let parse = |value| {
            parse_seconds(
                STOP_GRACE_VARIABLE,
                value,
                DEFAULT_STOP_GRACE,
                STOP_GRACE_MAX,
            )
        };
        assert_eq!(parse(None), Ok(Duration::from_secs(45)));
        assert_eq!(parse(Some("1")), Ok(Duration::from_secs(1)));
        assert_eq!(parse(Some("80")), Ok(Duration::from_secs(80)));
        for bad in ["", "0", "81", "90", "-1", "45s"] {
            assert!(parse(Some(bad)).is_err(), "{bad}");
        }
        assert_eq!(
            parse(Some("81")).unwrap_err(),
            "KORRI_STEAM_STOP_GRACE_SECONDS must be a whole number of seconds from 1 to 80"
        );
    }
    #[test]
    fn logon_timeout_defaults_to_15_seconds() {
        let parse = |value| {
            parse_seconds(
                LOGON_TIMEOUT_VARIABLE,
                value,
                DEFAULT_LOGON_TIMEOUT,
                LOGON_TIMEOUT_MAX,
            )
        };
        assert_eq!(parse(None), Ok(Duration::from_secs(15)));
        assert_eq!(parse(Some("300")), Ok(Duration::from_secs(300)));
        for bad in ["", "0", "301", "x"] {
            assert!(parse(Some(bad)).is_err(), "{bad}");
        }
    }
    const GRACE: Duration = Duration::from_secs(45);
    #[test]
    fn stop_signal_with_no_running_app_stops_at_once() {
        let now = Instant::now();
        let mut stop = StopControl::new(GRACE);
        assert_eq!(stop.poll(now, false), StopAction::Continue);
        assert_eq!(stop.signal(now), StopAction::StopNow);
        // An app that already exited is not pending.
        let mut stop = StopControl::new(GRACE);
        stop.command(CloudCommand::Launched(7));
        stop.command(CloudCommand::Exited(7));
        stop.command(CloudCommand::Sync(8));
        assert_eq!(stop.signal(now), StopAction::StopNow);
    }
    #[test]
    fn stop_signal_waits_for_exited_and_the_exit_sync() {
        let now = Instant::now();
        let mut stop = StopControl::new(GRACE);
        stop.command(CloudCommand::Launched(584400));
        assert_eq!(
            stop.signal(now),
            StopAction::Wait {
                pending: vec![584400],
                grace: GRACE
            }
        );
        assert_eq!(stop.poll(now, false), StopAction::Continue);
        // `exited` arrives; its exit job runs (busy), then finishes.
        stop.command(CloudCommand::Exited(584400));
        assert_eq!(stop.poll(now, true), StopAction::Continue);
        assert_eq!(
            stop.poll(now + Duration::from_secs(10), false),
            StopAction::StopNow
        );
    }
    #[test]
    fn stop_signal_repeated_keeps_the_first_deadline() {
        let now = Instant::now();
        let mut stop = StopControl::new(GRACE);
        stop.command(CloudCommand::Launched(1));
        assert!(matches!(stop.signal(now), StopAction::Wait { .. }));
        // systemd and the reaper both send SIGTERM; the second changes nothing.
        let later = now + Duration::from_secs(30);
        assert_eq!(stop.signal(later), StopAction::Continue);
        assert_eq!(stop.poll(later, false), StopAction::Continue);
        assert_eq!(
            stop.poll(now + GRACE, false),
            StopAction::Expired { pending: vec![1] }
        );
    }
    #[test]
    fn stop_wait_expires_while_the_exit_job_still_runs() {
        let now = Instant::now();
        let mut stop = StopControl::new(Duration::from_secs(1));
        stop.command(CloudCommand::Launched(2));
        stop.command(CloudCommand::Launched(3));
        assert_eq!(
            stop.signal(now),
            StopAction::Wait {
                pending: vec![2, 3],
                grace: Duration::from_secs(1)
            }
        );
        stop.command(CloudCommand::Exited(2));
        stop.command(CloudCommand::Exited(3));
        assert_eq!(stop.poll(now, true), StopAction::Continue);
        assert_eq!(
            stop.poll(now + Duration::from_secs(1), true),
            StopAction::Expired { pending: vec![] }
        );
    }
    #[test]
    fn stop_wait_lists_apps_as_json() {
        assert_eq!(appid_list(&[]), "[]");
        assert_eq!(appid_list(&[584400, 7]), "[584400,7]");
    }
    #[test]
    fn connecting_goes_online_or_falls_back_to_offline() {
        let now = Instant::now();
        let deadline = now + DEFAULT_LOGON_TIMEOUT;
        assert_eq!(
            connecting_step(now, deadline, false, None),
            ConnectStep::Wait
        );
        assert_eq!(
            connecting_step(now, deadline, true, None),
            ConnectStep::Online
        );
        assert_eq!(
            connecting_step(now, deadline, true, Some(103)),
            ConnectStep::Online
        );
        assert_eq!(
            connecting_step(now, deadline, false, Some(103)),
            ConnectStep::Fallback(FallbackReason::ConnectFailed(103))
        );
        assert_eq!(
            connecting_step(deadline, deadline, false, None),
            ConnectStep::Fallback(FallbackReason::Timeout)
        );
        assert_eq!(
            FallbackReason::ConnectFailed(102).json(),
            r#""reason":"connect_failed","callback":102"#
        );
        assert_eq!(FallbackReason::Timeout.json(), r#""reason":"timeout""#);
        assert_eq!(
            FallbackReason::LogOnRefused(3).json(),
            r#""reason":"logon_refused","eresult":3"#
        );
    }
    #[test]
    fn offline_logon_waits_for_logoff_then_runs_commands() {
        let now = Instant::now();
        let deadline = now + LEAVE_NETWORK_TIMEOUT;
        assert!(!left_network(now, deadline, 1));
        assert!(left_network(now, deadline, 0));
        assert!(left_network(deadline, deadline, 5));
        let connecting = LogonPhase::Connecting { deadline };
        let leaving = LogonPhase::LeavingNetwork { deadline };
        assert!(!session_ready(connecting, true));
        assert!(!session_ready(leaving, true));
        assert!(!session_ready(LogonPhase::Online, false));
        assert!(session_ready(LogonPhase::Online, true));
        // Offline: BLoggedOn need not be true for commands to run (and report offline).
        assert!(session_ready(LogonPhase::Offline, false));
        const { assert!(OFFLINE_MODE) };
        assert_eq!(ERESULT_OK, 1);
    }
    /// The engine map gives each method of one table its own slot and a real RVA.
    fn distinct_slots(table: &[(usize, usize)]) {
        let mut slots: Vec<usize> = table.iter().map(|s| s.0).collect();
        slots.sort_unstable();
        slots.dedup();
        assert_eq!(slots.len(), table.len(), "{table:x?}");
        assert!(table.iter().all(|s| s.1 > 0x1000), "{table:x?}");
    }
    #[test]
    fn engine_map_slots_are_distinct_per_table() {
        if !ENGINE_MAP_PRESENT {
            return;
        }
        distinct_slots(&[
            ENGINE_CREATE_STEAM_PIPE,
            ENGINE_RELEASE_STEAM_PIPE,
            ENGINE_CREATE_GLOBAL_USER,
            ENGINE_CONNECT_TO_GLOBAL_USER,
            ENGINE_RELEASE_USER,
            ENGINE_GET_USER,
            ENGINE_RUN_FRAME,
            ENGINE_GET_REMOTE_STORAGE,
            ENGINE_GET_APP_MANAGER,
            ENGINE_SET_COMMAND_LINE,
        ]);
        distinct_slots(&USER_PROXY_SLOTS);
        if let Some(rvas) = USER_LOCAL_RVAS {
            assert!(rvas.iter().all(|r| *r > 0x1000));
        }
        distinct_slots(&[
            IS_CLOUD_ENABLED_FOR_ACCOUNT,
            IS_CLOUD_ENABLED_FOR_APP,
            LOAD_LOCAL_FILE_INFO_CACHE,
            EVALUATE_SYNC_STATE,
            GET_SYNC_STATE,
            GET_CONFLICTING_FILE_TIMESTAMPS,
            SYNCHRONIZE_APP,
            IS_APP_SYNC_IN_PROGRESS,
            RUN_AUTOCLOUD_ON_LAUNCH,
            RUN_AUTOCLOUD_ON_EXIT,
            RESOLVE_SYNC_CONFLICT,
        ]);
        distinct_slots(&[
            INSTALL_APP,
            UNINSTALL_APP,
            GET_APP_INSTALL_STATE,
            GET_UPDATE_INFO,
            IS_APP_UP_TO_DATE,
            IS_DOWNLOADING_ENABLED,
            GET_DOWNLOADING_APP_ID,
            GET_NUM_APPS_IN_DOWNLOAD_QUEUE,
        ]);
        assert_eq!(ENGINE_SHA256.len(), 64);
        assert!(CLIENT_ENGINE_VERSION
            .to_str()
            .unwrap()
            .starts_with("CLIENTENGINE_INTERFACE_VERSION"));
    }
    #[test]
    fn autocloud_commands_start_the_queue_after_setting_their_bit() {
        use CloudCall::*;
        assert_eq!(first_calls(JobKind::Launch), [LoadLocalFileInfoCache]);
        assert_eq!(
            first_calls(JobKind::Exit),
            [RunAutoCloudOnAppExit, LoadLocalFileInfoCache]
        );
        assert!(first_calls(JobKind::Sync).is_empty());
        assert_eq!(LoadLocalFileInfoCache.slot(), LOAD_LOCAL_FILE_INFO_CACHE.0);
        assert_eq!(RunAutoCloudOnAppExit.name(), "RunAutoCloudOnAppExit");
    }
    #[test]
    fn cloud_runs_only_when_the_account_and_the_app_allow_it() {
        assert!(cloud_allowed(true, true));
        assert!(!cloud_allowed(false, true));
        assert!(!cloud_allowed(true, false));
        assert!(!cloud_allowed(false, false));
    }
    #[test]
    fn exit_job_evaluates_after_the_autocloud_pass_then_uploads() {
        use JobKind::Exit;
        assert_eq!(next_step(Exit, 3, true, done(0, 0)), SyncStep::Wait);
        assert_eq!(next_step(Exit, 2, false, done(0, 0)), SyncStep::Evaluate);
        assert_eq!(next_step(Exit, 5, false, done(1, 0)), SyncStep::Upload);
        assert_eq!(
            next_step(Exit, 2, false, done(1, 1)),
            SyncStep::Finish("synchronized")
        );
    }
    #[test]
    fn app_manager_install_arguments() {
        assert_eq!((DEFAULT_LIBRARY_FOLDER, APP_UPDATE_OK), (-1, 0));
    }
    #[test]
    fn update_info_reads_the_appmanifest_byte_fields() {
        let mut raw = [0u8; UPDATE_INFO_SIZE];
        raw[0x80..0x88].copy_from_slice(&1000u64.to_le_bytes());
        raw[0x88..0x90].copy_from_slice(&97_849_494u64.to_le_bytes());
        raw[0x98..0xa0].copy_from_slice(&3u64.to_le_bytes());
        raw[0xa0..0xa8].copy_from_slice(&4u64.to_le_bytes());
        raw[0x3c..0x40].copy_from_slice(&6u32.to_le_bytes());
        assert_eq!(
            parse_update_info(&raw),
            UpdateInfo {
                bytes_downloaded: 1000,
                bytes_to_download: 97_849_494,
                bytes_staged: 3,
                bytes_to_stage: 4,
                update_result: 6,
            }
        );
    }
    #[test]
    fn install_finishes_only_when_fully_installed_idle_and_up_to_date() {
        let install = AppCommand::Install(78000);
        assert_eq!(
            app_step(install, 4, true, None),
            AppStep::Finish("installed")
        );
        // Fully installed but an update is required, running, or the app is stale.
        assert_eq!(app_step(install, 6, true, None), AppStep::Wait);
        assert_eq!(app_step(install, 4 | 0x100, true, None), AppStep::Wait);
        assert_eq!(app_step(install, 4, false, None), AppStep::Wait);
        // Seen on the device: Update Required | Update Queued, then | Update
        // Running | Update Started, then Fully Installed | Update Queued (| Running).
        for state in [0xa, 0x50a, 0x10c, 0xc] {
            assert_eq!(app_step(install, state, true, None), AppStep::Wait);
        }
        assert_eq!(app_step(install, 1, false, None), AppStep::Wait);
        let paused = 0x200 | 0x2;
        let info = UpdateInfo {
            update_result: 6,
            ..UpdateInfo::default()
        };
        assert!(install_stalled(paused, info));
        assert!(!install_stalled(paused, UpdateInfo::default()));
        assert!(!install_stalled(0x2, info));
        assert_eq!(
            app_step(install, paused, false, Some(Duration::from_secs(5))),
            AppStep::Wait
        );
        assert_eq!(
            app_step(install, paused, false, Some(INSTALL_STALL_LIMIT)),
            AppStep::Finish("install_failed")
        );
    }
    #[test]
    fn uninstall_finishes_when_the_engine_reports_uninstalled() {
        let uninstall = AppCommand::Uninstall(78000);
        assert_eq!(
            app_step(uninstall, 1, false, None),
            AppStep::Finish("uninstalled")
        );
        assert_eq!(app_step(uninstall, 4 | 0x800, true, None), AppStep::Wait);
        assert_eq!(app_step(uninstall, 4, true, None), AppStep::Wait);
    }
    #[test]
    fn state_names_list_the_set_bits() {
        assert_eq!(state_names(0), "[]");
        assert_eq!(state_names(4), r#"["Fully Installed"]"#);
        // The device's install: "Fully Installed,Update Queued,Update Running,".
        assert_eq!(
            state_names(0x10c),
            r#"["Fully Installed","Update Queued","Update Running"]"#
        );
        assert_eq!(update_error_name(0), "No Error");
        assert_eq!(update_error_name(29), "Invalid platform");
        assert_eq!(update_error_name(32), "Download disabled");
        assert_eq!(update_error_name(39), "File locked");
        assert_eq!(update_error_name(40), "unknown");
    }
    #[test]
    fn install_timeout_defaults_to_an_hour() {
        let parse = |value| {
            parse_seconds(
                INSTALL_TIMEOUT_VARIABLE,
                value,
                DEFAULT_INSTALL_TIMEOUT,
                INSTALL_TIMEOUT_MAX,
            )
        };
        assert_eq!(parse(None), Ok(Duration::from_secs(3600)));
        assert_eq!(parse(Some("86400")), Ok(Duration::from_secs(86400)));
        for bad in ["", "0", "86401", "1h"] {
            assert!(parse(Some(bad)).is_err(), "{bad}");
        }
    }

    // ---- product host (ADR 0083) ----
    #[test]
    fn parse_command_accepts_the_product_verbs() {
        assert_eq!(parse_command("signin-qr"), Ok(Some(Command::SigninQr)));
        assert_eq!(parse_command(" signout \n"), Ok(Some(Command::Signout)));
        assert_eq!(parse_command("list-apps"), Ok(Some(Command::ListApps)));
        assert_eq!(
            parse_command("resolve 584400 local"),
            Ok(Some(Command::Cloud(CloudCommand::Resolve(584400, true))))
        );
        assert_eq!(
            parse_command("resolve 584400 cloud"),
            Ok(Some(Command::Cloud(CloudCommand::Resolve(584400, false))))
        );
        assert_eq!(CloudCommand::Resolve(7, true).name(), "resolve");
        assert_eq!(CloudCommand::Resolve(7, true).appid(), 7);
    }
    #[test]
    fn parse_command_rejects_bad_product_lines() {
        use CommandError::*;
        assert_eq!(parse_command("signin-qr now"), Err(ExtraArguments));
        assert_eq!(parse_command("list-apps 5"), Err(ExtraArguments));
        assert_eq!(parse_command("resolve 5"), Err(InvalidSide));
        assert_eq!(parse_command("resolve 5 LOCAL"), Err(InvalidSide));
        assert_eq!(parse_command("resolve 5 local extra"), Err(ExtraArguments));
        assert_eq!(parse_command("resolve 0 local"), Err(InvalidAppId));
        assert_eq!(parse_command("resolve"), Err(MissingAppId));
        assert_eq!(InvalidSide.name(), "invalid_side");
    }
    #[test]
    fn resolve_job_waits_then_reports_what_the_engine_did() {
        let p = Progress::default();
        assert_eq!(next_step(JobKind::Resolve, 3, true, p), SyncStep::Wait);
        assert_eq!(
            next_step(JobKind::Resolve, 2, false, p),
            SyncStep::Finish("resolved")
        );
        assert_eq!(
            next_step(JobKind::Resolve, 7, false, p),
            SyncStep::Finish("conflict_not_resolved")
        );
        assert_eq!(next_step(JobKind::Resolve, 8, false, p), SyncStep::Evaluate);
        assert_eq!(next_step(JobKind::Resolve, 5, false, p), SyncStep::Upload);
        assert!(first_calls(JobKind::Resolve).is_empty());
        assert_eq!(JobKind::Resolve.name(), "resolve");
    }
    #[test]
    fn session_is_over_once_the_lock_was_held_freed_and_the_exit_sync_ran() {
        let now = Instant::now();
        let mut idle = None;
        // Before the shim took the lock: wait (the idle clock runs).
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, false, vec![], false),
            SessionAction::Continue
        );
        // Freed with the exit job still running: wait for it.
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, true, vec![], true),
            SessionAction::Continue
        );
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, true, vec![], false),
            SessionAction::Over
        );
        // Job mode never sees a lock: only the idle stop ends it.
        let mut idle = None;
        assert_eq!(
            session_step(&mut idle, IDLE, now, false, false, vec![], false),
            SessionAction::Continue
        );
        assert_eq!(
            session_step(&mut idle, IDLE, now + IDLE, false, false, vec![], false),
            SessionAction::IdleStop
        );
    }
    #[test]
    fn engine_check_reports_a_missing_map_and_a_mismatched_engine() {
        let (event, _) = engine_check(false, "", || unreachable!()).unwrap_err();
        assert_eq!(event, r#"{"event":"engine_map_missing"}"#);
        let (event, _) = engine_check(true, "aa", || Ok("bb".into())).unwrap_err();
        assert_eq!(
            event,
            r#"{"event":"engine_mismatch","expected":"aa","found":"bb"}"#
        );
        assert!(engine_check(true, "aa", || Ok("aa".into())).is_ok());
        let (event, error) = engine_check(true, "aa", || Err("cannot read".into())).unwrap_err();
        assert!(event.is_empty() && error == "cannot read");
    }
    #[test]
    fn file_sha256_matches_a_known_digest() {
        let path = std::env::temp_dir().join(format!("korri-sha-{}", std::process::id()));
        std::fs::write(&path, b"abc").unwrap();
        assert_eq!(
            file_sha256(&path).unwrap(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn json_strings_are_escaped() {
        assert_eq!(json_string("a\"b\\c\n\u{1}"), r#""a\"b\\c\n\u0001""#);
        assert_eq!(
            json_string("https://s.team/q/1/2"),
            r#""https://s.team/q/1/2""#
        );
    }
    #[test]
    fn account_file_round_trips_and_refuses_junk() {
        let dir = std::env::temp_dir().join(format!("korri-account-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(ACCOUNT_FILE);
        assert_eq!(read_account(&path), None);
        write_account(&path, c"player_one").unwrap();
        assert_eq!(read_account(&path).as_deref(), Some(c"player_one"));
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(
            std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o600
        );
        std::fs::write(&path, "  \n").unwrap();
        assert_eq!(read_account(&path), None);
        std::fs::write(&path, "x".repeat(MAX_ACCOUNT_NAME + 1)).unwrap();
        assert_eq!(read_account(&path), None);
        std::fs::write(dir.join(LOGIN_STORE), "store").unwrap();
        std::fs::write(&path, "player_one").unwrap();
        forget(&path, &dir);
        assert!(!path.exists() && !dir.join(LOGIN_STORE).exists());
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn engine_refusal_is_the_protocol_version_eresult_only() {
        assert!(refused_engine(7));
        for other in [1, 2, 3, 5, 20, 55] {
            assert!(!refused_engine(other), "{other}");
        }
    }
    #[test]
    fn list_apps_reports_owned_and_free_games_with_their_names() {
        use appinfo::tests::{Writer, W::*};
        let dir = std::env::temp_dir().join(format!("korri-list-{}", std::process::id()));
        std::fs::create_dir_all(dir.join("appcache")).unwrap();
        let file = Writer::file(&[
            (
                10,
                O(vec![(
                    "common",
                    O(vec![("name", S("Owned \"One\"")), ("type", S("Game"))]),
                )]),
            ),
            (
                20,
                O(vec![(
                    "common",
                    O(vec![("name", S("Free")), ("type", S("game"))]),
                )]),
            ),
            (
                30,
                O(vec![(
                    "common",
                    O(vec![("name", S("Server")), ("type", S("Tool"))]),
                )]),
            ),
        ]);
        std::fs::write(dir.join("appcache/appinfo.vdf"), file).unwrap();
        let out_path = dir.join("out.jsonl");
        let mut out = File::create(&out_path).unwrap();
        let subscribed = |free: bool| if free { vec![10, 20, 30, 40] } else { vec![10] };
        list_apps(&mut out, &subscribed, &dir).unwrap();
        let text = std::fs::read_to_string(&out_path).unwrap();
        assert_eq!(
            text.lines().collect::<Vec<_>>(),
            vec![
                r#"{"event":"app","appid":10,"name":"Owned \"One\"","source":"owned"}"#,
                r#"{"event":"app","appid":20,"name":"Free","source":"free"}"#,
                r#"{"event":"apps_skipped","no_appinfo":1,"not_game":1}"#,
                r#"{"event":"apps_done"}"#,
            ]
        );
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn make_fifo_creates_once_and_refuses_a_plain_file() {
        let dir = std::env::temp_dir().join(format!("korri-fifo-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let fifo = dir.join("commands");
        make_fifo(&fifo).unwrap();
        assert!(std::fs::metadata(&fifo).unwrap().file_type().is_fifo());
        make_fifo(&fifo).unwrap();
        std::fs::write(dir.join("plain"), "").unwrap();
        assert!(make_fifo(&dir.join("plain")).is_err());
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn start_login_names_why_it_is_signed_out() {
        let never = |_: &CStr| -> bool { unreachable!() };
        let no_select = |_: &CStr| -> u64 { unreachable!() };
        assert_eq!(
            start_login(None, never, no_select),
            Err(SignedOutReason::NoAccountFile)
        );
        assert_eq!(
            start_login(Some(c"player".into()), |_| false, no_select),
            Err(SignedOutReason::NoSavedLogin)
        );
        assert_eq!(
            start_login(Some(c"player".into()), |_| true, |_| 0),
            Err(SignedOutReason::SelectFailed)
        );
        // A SteamID whose account part is 0 is no account.
        assert_eq!(
            start_login(Some(c"player".into()), |_| true, |_| 1 << 52),
            Err(SignedOutReason::SelectFailed)
        );
        assert_eq!(
            start_login(
                Some(c"player".into()),
                |name| name == c"player",
                |_| 76561197960265770
            ),
            Ok((c"player".into(), 76561197960265770))
        );
        let names: Vec<&str> = [
            SignedOutReason::NoAccountFile,
            SignedOutReason::NoSavedLogin,
            SignedOutReason::SelectFailed,
        ]
        .map(SignedOutReason::name)
        .to_vec();
        assert_eq!(
            names,
            ["no_account_file", "no_saved_login", "select_failed"]
        );
    }
    #[test]
    fn refused_takes_only_a_known_reason_word() {
        for refusal in Refusal::ALL {
            assert_eq!(
                parse_command(&format!("refused {}", refusal.name())),
                Ok(Some(Command::Refused(refusal)))
            );
            assert!(refusal.message().starts_with("Steam engine: "));
        }
        assert_eq!(parse_command("refused"), Err(CommandError::InvalidReason));
        assert_eq!(
            parse_command("refused Steam engine: free text"),
            Err(CommandError::InvalidReason)
        );
        assert_eq!(
            parse_command("refused install_failed now"),
            Err(CommandError::ExtraArguments)
        );
        assert_eq!(CommandError::InvalidReason.name(), "invalid_reason");
    }
    #[test]
    fn a_qr_login_counts_as_saved_only_after_the_engine_writes_config_vdf() {
        use std::time::{Duration as D, SystemTime};
        let start = Instant::now();
        let before = SystemTime::UNIX_EPOCH + D::from_secs(1000);
        let after = before + D::from_secs(5);
        let mut save = LoginSave {
            since: start,
            baseline: Some(before),
            changed_at: None,
        };
        // local.vdf written at SetLoginToken, config.vdf not yet: wait.
        assert_eq!(
            login_save_step(&mut save, start, Some(before), true),
            SaveStep::Wait
        );
        // config.vdf written: wait for the settle time, then saved.
        let t = start + D::from_millis(500);
        assert_eq!(
            login_save_step(&mut save, t, Some(after), true),
            SaveStep::Wait
        );
        assert_eq!(
            login_save_step(&mut save, t + LOGIN_SAVE_SETTLE, Some(after), true),
            SaveStep::Saved
        );
        // Without local.vdf the login is not saved, whatever config.vdf does.
        let mut save = LoginSave {
            since: start,
            baseline: None,
            changed_at: None,
        };
        assert_eq!(
            login_save_step(&mut save, start + D::from_secs(5), Some(after), false),
            SaveStep::Wait
        );
        // A first config.vdf counts as a write.
        assert_eq!(
            login_save_step(&mut save, start + D::from_secs(5), Some(after), true),
            SaveStep::Wait
        );
        assert_eq!(
            login_save_step(&mut save, start + D::from_secs(7), Some(after), true),
            SaveStep::Saved
        );
        // Nothing written: give up after the limit, unconfirmed.
        let mut save = LoginSave {
            since: start,
            baseline: Some(before),
            changed_at: None,
        };
        assert_eq!(
            login_save_step(&mut save, start + LOGIN_SAVE_TIMEOUT, Some(before), true),
            SaveStep::Unconfirmed
        );
    }
    /// A login saved by one host process is found by the next: the account
    /// name file outlives the process, and start_login reads it back.
    #[test]
    fn a_saved_login_is_selected_by_a_new_host_process() {
        let dir = std::env::temp_dir().join(format!("korri-relogin-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(ACCOUNT_FILE);
        let account = c"player_one";
        // The QR host process writes the name and exits.
        let writer = std::process::Command::new("sh")
            .arg("-c")
            .arg("umask 077; printf %s \"$1\" > \"$2\"")
            .arg("sh")
            .arg(account.to_str().unwrap())
            .arg(&path)
            .status()
            .unwrap();
        assert!(writer.success());
        // A new process reads it, and the engine's cached login selects it.
        let started = start_login(
            read_account(&path),
            |name| name == account,
            |_| 76561197960265770,
        );
        assert_eq!(started, Ok((account.into(), 76561197960265770)));
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn list_apps_waits_for_the_licences_to_arrive_and_settle() {
        let start = Instant::now();
        let at = |ms: u64| start + Duration::from_millis(ms);
        let mut wait = ListWait::new(start);
        // Signed in, no licence yet (the device case): keep waiting.
        assert!(!licences_settled(&mut wait, at(0), 0));
        assert!(!licences_settled(&mut wait, at(5_000), 0));
        // Licences arrive in batches; the count must hold still.
        assert!(!licences_settled(&mut wait, at(6_000), 120));
        assert!(!licences_settled(&mut wait, at(7_000), 480));
        assert!(!licences_settled(&mut wait, at(9_000), 480));
        assert!(licences_settled(&mut wait, at(10_000), 480));
        // An account with no licence at all lists nothing after the limit.
        let mut wait = ListWait::new(start);
        assert!(!licences_settled(&mut wait, at(10_000), 0));
        assert!(licences_settled(&mut wait, start + LICENCE_TIMEOUT, 0));
    }
    #[test]
    fn list_apps_waits_once_for_missing_appinfo_records() {
        use std::time::UNIX_EPOCH;
        let start = Instant::now();
        let before = Some(UNIX_EPOCH + Duration::from_secs(10));
        let after = Some(UNIX_EPOCH + Duration::from_secs(20));
        let mut wait = ListWait::Appinfo {
            since: start,
            baseline: before,
            changed_at: None,
        };
        assert!(!appinfo_written(&mut wait, start, before));
        assert!(!appinfo_written(
            &mut wait,
            start + Duration::from_secs(2),
            after
        ));
        assert!(appinfo_written(
            &mut wait,
            start + Duration::from_secs(2) + APPINFO_SETTLE,
            after
        ));
        let mut wait = ListWait::Appinfo {
            since: start,
            baseline: None,
            changed_at: None,
        };
        assert!(appinfo_written(&mut wait, start + APPINFO_TIMEOUT, None));
        // Counting is against the cache on disk.
        let dir = std::env::temp_dir().join(format!("korri-appinfo-{}", std::process::id()));
        std::fs::create_dir_all(dir.join("appcache")).unwrap();
        use appinfo::tests::{Writer, W::*};
        let file = Writer::file(&[(10, O(vec![("common", O(vec![("name", S("A"))]))]))]);
        std::fs::write(dir.join("appcache/appinfo.vdf"), file).unwrap();
        assert_eq!(apps_without_appinfo(&[10, 20, 30], &dir), 2);
        std::fs::remove_dir_all(dir).unwrap();
    }
}
