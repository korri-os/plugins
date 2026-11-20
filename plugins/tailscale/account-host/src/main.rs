//! The Tailscale plugin's account host (Core ADR 0089).
//!
//! Korri's plugin host runs this program for one connection from korrid,
//! beside `tailscaled`, as tailscaled's own user and in its runtime folder.
//! Its input and output are that connection. It reads one command per line
//! (`status`, `signin-qr`, `signout`) and writes one JSON event per line
//! (`qr_code`, `qr_refreshed`, `signed_in`, `signin_failed`, `signed_out`),
//! the account subset of the Steam engine host's protocol. It ends at the end
//! of its input.
//!
//! It drives the plugin's own `tailscale` CLI against the plugin's socket:
//! `status --json` gives the state, `up --json` the login link. With the
//! admitted credential `authkey` (Core ADR 0034), `up` uses it instead of a
//! link. It never prints the key or the link to its error output.
use serde_json::{json, Value};
use std::{
    io::{BufRead, Read, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::mpsc,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

/// The plugin's own CLI, fixed at build time. Tests may name another.
fn cli() -> PathBuf {
    std::env::var_os("KORRI_TAILSCALE_CLI")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("KORRI_TAILSCALE_CLI")))
}

/// tailscaled's socket in the runtime folder the unit shares with it.
fn socket() -> Option<PathBuf> {
    let folder = std::env::var_os("RUNTIME_DIRECTORY")?;
    // systemd lists several folders with `:`; the plugin's is the first.
    let first = folder.to_str()?.split(':').next()?.to_owned();
    (!first.is_empty()).then(|| PathBuf::from(first).join("tailscaled.sock"))
}

/// The admitted credential's file, when systemd delivered a non-empty one.
fn auth_key() -> Option<PathBuf> {
    let path = PathBuf::from(std::env::var_os("CREDENTIALS_DIRECTORY")?).join("authkey");
    std::fs::metadata(&path)
        .ok()
        .filter(|metadata| metadata.is_file() && metadata.len() > 0)
        .map(|_| path)
}

fn emit(event: Value) {
    let mut out = std::io::stdout().lock();
    // A closed connection ends the program at its next read.
    let _ = writeln!(out, "{event}");
    let _ = out.flush();
}

fn failed(reason: &str) {
    emit(json!({"event": "signin_failed", "reason": reason}));
}

enum Message {
    Line(String),
    End,
    /// One JSON block from `tailscale up --json`.
    Up(Value),
    /// `tailscale up` ended.
    UpEnded(bool),
}

/// What `tailscale status --json` says about the sign-in.
#[derive(Debug, PartialEq)]
enum Account {
    SignedIn(String),
    SignedOut {
        expired: bool,
    },
    /// Signed in, but an administrator must approve the device.
    NeedsApproval,
}

/// `status --json` to an account. `now` is Unix seconds.
fn account(status: &Value, now: i64) -> Account {
    let state = status["BackendState"].as_str().unwrap_or_default();
    let me = &status["Self"];
    let login = me["UserID"]
        .as_i64()
        .filter(|id| *id != 0)
        .and_then(|id| status["User"][id.to_string()]["LoginName"].as_str())
        .map(str::to_owned);
    match (state, login) {
        ("NeedsMachineAuth", _) => Account::NeedsApproval,
        ("Running" | "Starting" | "Stopped", Some(login)) => Account::SignedIn(login),
        _ => {
            let key_expired = me["Expired"].as_bool() == Some(true)
                || me["KeyExpiry"]
                    .as_str()
                    .and_then(unix_seconds)
                    .is_some_and(|expiry| expiry <= now);
            let health_says = status["Health"].as_array().is_some_and(|health| {
                health
                    .iter()
                    .filter_map(Value::as_str)
                    .any(|line| line.to_ascii_lowercase().contains("expired"))
            });
            Account::SignedOut {
                expired: state == "NeedsLogin" && (key_expired || health_says),
            }
        }
    }
}

/// RFC 3339 (`2026-11-20T10:00:00Z`, `...+01:00`, fractions allowed) to
/// Unix seconds.
fn unix_seconds(text: &str) -> Option<i64> {
    let number = |range: std::ops::Range<usize>| text.get(range)?.parse::<i64>().ok();
    let (year, month, day) = (number(0..4)?, number(5..7)?, number(8..10)?);
    let (hour, minute, second) = (number(11..13)?, number(14..16)?, number(17..19)?);
    if text.get(4..5)? != "-" || !matches!(text.get(10..11)?, "T" | "t" | " ") {
        return None;
    }
    let mut rest = text.get(19..)?;
    if let Some(fraction) = rest.strip_prefix('.') {
        rest = fraction.trim_start_matches(|c: char| c.is_ascii_digit());
    }
    let offset = match rest {
        "Z" | "z" => 0,
        _ => {
            let sign = match rest.get(0..1)? {
                "+" => 1,
                "-" => -1,
                _ => return None,
            };
            let hours = rest.get(1..3)?.parse::<i64>().ok()?;
            let minutes = rest.get(4..6)?.parse::<i64>().ok()?;
            sign * (hours * 3600 + minutes * 60)
        }
    };
    // Howard Hinnant's days_from_civil.
    let y = if month <= 2 { year - 1 } else { year };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (month + 9) % 12;
    let doy = (153 * mp + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146_097 + doe - 719_468;
    Some(days * 86_400 + hour * 3600 + minute * 60 + second - offset)
}

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or_default()
}

/// `tailscale --socket=S <args>`, its output and whether it succeeded,
/// bounded by `limit`.
fn run(socket: &Path, args: &[&str], limit: Duration) -> Option<(bool, Vec<u8>)> {
    let mut child = Command::new(cli())
        .arg(format!("--socket={}", socket.display()))
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let mut stdout = child.stdout.take()?;
    let reader = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        let _ = stdout.read_to_end(&mut bytes);
        bytes
    });
    let deadline = std::time::Instant::now() + limit;
    let status = loop {
        if let Some(status) = child.try_wait().ok()? {
            break status;
        }
        if std::time::Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            return None;
        }
        std::thread::sleep(Duration::from_millis(50));
    };
    Some((status.success(), reader.join().ok()?))
}

fn read_account(socket: &Path) -> Option<Account> {
    // `status` exits non-zero while logged out; its JSON still says why.
    let (_, out) = run(socket, &["status", "--json"], Duration::from_secs(20))?;
    let status: Value = serde_json::from_slice(&out).ok()?;
    status.is_object().then(|| account(&status, now()))
}

fn report(account: Account) {
    match account {
        Account::SignedIn(login) => emit(json!({"event": "signed_in", "account_name": login})),
        Account::SignedOut { expired: true } => {
            emit(json!({"event": "signed_out", "reason": "expired"}))
        }
        Account::SignedOut { expired: false } => emit(json!({"event": "signed_out"})),
        Account::NeedsApproval => emit(json!({"event": "signed_out", "reason": "needs_approval"})),
    }
}

fn status(socket: &Path) {
    match read_account(socket) {
        Some(account) => report(account),
        None => failed("daemon_unreachable"),
    }
}

fn sign_out(socket: &Path) {
    let _ = run(socket, &["logout"], Duration::from_secs(30));
    match read_account(socket) {
        Some(Account::SignedIn(_)) => failed("logout_failed"),
        Some(_) => emit(json!({"event": "signed_out"})),
        None => failed("daemon_unreachable"),
    }
}

/// Bounds the CLI's own wait; korrid gives up after 15 minutes.
const UP_TIMEOUT: &str = "--timeout=890s";

/// `up --json`: each new login link is a code; Running is the sign-in.
/// Returns false when the input ended, which ends the program.
fn sign_in(
    socket: &Path,
    messages: &mpsc::Receiver<Message>,
    send: &mpsc::Sender<Message>,
) -> bool {
    let key = auth_key();
    let mut command = Command::new(cli());
    command.arg(format!("--socket={}", socket.display())).args([
        "up",
        "--json",
        "--accept-dns=false",
        UP_TIMEOUT,
    ]);
    if let Some(key) = &key {
        command.arg(format!("--auth-key=file:{}", key.display()));
    }
    let mut child = match command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(child) => child,
        Err(_) => {
            failed("cli_missing");
            return true;
        }
    };
    let Some(stdout) = child.stdout.take() else {
        failed("cli_missing");
        return true;
    };
    let blocks = send.clone();
    std::thread::spawn(move || {
        // Pretty-printed JSON blocks, one after another.
        for block in serde_json::Deserializer::from_reader(stdout).into_iter::<Value>() {
            match block {
                Ok(block) => {
                    if blocks.send(Message::Up(block)).is_err() {
                        return;
                    }
                }
                Err(_) => break,
            }
        }
    });
    let waiter = send.clone();
    let child = std::sync::Arc::new(std::sync::Mutex::new(child));
    let watched = std::sync::Arc::clone(&child);
    std::thread::spawn(move || loop {
        let done = watched
            .lock()
            .map(|mut c| c.try_wait())
            .ok()
            .and_then(Result::ok);
        if let Some(status) = done.flatten() {
            let _ = waiter.send(Message::UpEnded(status.success()));
            return;
        }
        std::thread::sleep(Duration::from_millis(100));
    });
    let stop = |child: &std::sync::Arc<std::sync::Mutex<std::process::Child>>| {
        if let Ok(mut child) = child.lock() {
            let _ = child.kill();
        }
    };
    let mut shown: Option<String> = None;
    let mut error: Option<String> = None;
    loop {
        match messages.recv() {
            Ok(Message::Up(block)) => {
                if let Some(url) = block["AuthURL"]
                    .as_str()
                    .filter(|u| u.starts_with("https://"))
                {
                    let event = if shown.is_none() {
                        "qr_code"
                    } else {
                        "qr_refreshed"
                    };
                    if shown.as_deref() != Some(url) {
                        emit(json!({"event": event, "challenge_url": url}));
                        shown = Some(url.to_owned());
                    }
                }
                if let Some(message) = block["Error"].as_str().filter(|m| !m.is_empty()) {
                    error = Some(message.to_owned());
                }
                if block["BackendState"].as_str() == Some("NeedsMachineAuth") {
                    error = Some("needs_approval".into());
                }
            }
            Ok(Message::UpEnded(success)) => {
                match read_account(socket) {
                    Some(Account::SignedIn(login)) => {
                        emit(json!({"event": "signed_in", "account_name": login}))
                    }
                    Some(Account::NeedsApproval) => failed("needs_approval"),
                    _ if error.as_deref() == Some("needs_approval") => failed("needs_approval"),
                    _ if success => failed("not_running"),
                    _ if key.is_some() => failed("auth_key_refused"),
                    _ => failed("timeout"),
                }
                return true;
            }
            // korrid sends nothing else while a sign-in runs.
            Ok(Message::Line(_)) => {}
            Ok(Message::End) | Err(_) => {
                stop(&child);
                return false;
            }
        }
    }
}

fn main() {
    let Some(socket) = socket() else {
        failed("no_runtime_directory");
        return;
    };
    let (send, messages) = mpsc::channel();
    let lines = send.clone();
    std::thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            if lines.send(Message::Line(line)).is_err() {
                return;
            }
        }
        let _ = lines.send(Message::End);
    });
    loop {
        match messages.recv() {
            Ok(Message::Line(line)) => match line.trim() {
                "status" => status(&socket),
                "signin-qr" => {
                    if !sign_in(&socket, &messages, &send) {
                        return;
                    }
                }
                "signout" => sign_out(&socket),
                // An unknown command is ignored, as korrid ignores unknown events.
                _ => {}
            },
            // Output of an earlier `up` that already ended.
            Ok(Message::Up(_) | Message::UpEnded(_)) => {}
            Ok(Message::End) | Err(_) => return,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rfc3339_times_are_unix_seconds() {
        assert_eq!(unix_seconds("1970-01-01T00:00:00Z"), Some(0));
        assert_eq!(unix_seconds("2026-11-20T10:00:00Z"), Some(1_795_168_800));
        assert_eq!(
            unix_seconds("2026-11-20T11:00:00.123456789+01:00"),
            Some(1_795_168_800)
        );
        assert_eq!(unix_seconds("2000-02-29T00:00:00-00:30"), Some(951_784_200));
        assert_eq!(unix_seconds("not a time"), None);
    }

    fn status(state: &str, me: Value) -> Value {
        json!({"BackendState": state, "Self": me,
            "User": {"42": {"ID": 42, "LoginName": "p@example.com", "DisplayName": "P"}}})
    }

    #[test]
    fn status_maps_to_the_sign_in() {
        let now = 1_795_168_800;
        assert_eq!(
            account(&status("Running", json!({"UserID": 42})), now),
            Account::SignedIn("p@example.com".into())
        );
        assert_eq!(
            account(&status("Stopped", json!({"UserID": 42})), now),
            Account::SignedIn("p@example.com".into())
        );
        assert_eq!(
            account(&status("NeedsLogin", json!({"UserID": 0})), now),
            Account::SignedOut { expired: false }
        );
        assert_eq!(
            account(&json!({"BackendState": "NoState"}), now),
            Account::SignedOut { expired: false }
        );
        // The node key ran out: needs sign-in again.
        assert_eq!(
            account(
                &status(
                    "NeedsLogin",
                    json!({"UserID": 42, "KeyExpiry": "2026-11-01T00:00:00Z"})
                ),
                now
            ),
            Account::SignedOut { expired: true }
        );
        assert_eq!(
            account(
                &status("NeedsLogin", json!({"UserID": 42, "Expired": true})),
                now
            ),
            Account::SignedOut { expired: true }
        );
        assert_eq!(
            account(
                &status(
                    "NeedsLogin",
                    json!({"UserID": 42, "KeyExpiry": "2027-01-01T00:00:00Z"})
                ),
                now
            ),
            Account::SignedOut { expired: false }
        );
        let mut health = status("NeedsLogin", json!({"UserID": 42}));
        health["Health"] = json!(["Your node key has expired; log in again."]);
        assert_eq!(account(&health, now), Account::SignedOut { expired: true });
        assert_eq!(
            account(&status("NeedsMachineAuth", json!({"UserID": 42})), now),
            Account::NeedsApproval
        );
    }
}
