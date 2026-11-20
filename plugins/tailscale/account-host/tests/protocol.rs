//! The account host against a fake `tailscale` CLI: the line protocol korrid
//! speaks (Core `services/korrid/src/account_sign_in/protocol.rs`).
use serde_json::Value;
use std::{
    io::{BufRead, BufReader, Write},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc,
    time::{Duration, Instant},
};

/// Answers `status`, `up` and `logout` from files beside `$FAKE_STATE`, and
/// records its arguments.
const FAKE_CLI: &str = r#"#!/bin/sh
state="$FAKE_STATE"
echo "$@" >> "$state.args"
key=
for a in "$@"; do
  case "$a" in
    status|up|logout) cmd="$a" ;;
    --auth-key=file:*) key="${a#--auth-key=file:}" ;;
  esac
done
case "$cmd" in
  status)
    if [ -e "$state.in" ]; then
      printf '{"BackendState":"Running","Self":{"UserID":42},"User":{"42":{"LoginName":"p@example.com"}}}\n'
    elif [ -e "$state.expired" ]; then
      printf '{"BackendState":"NeedsLogin","Self":{"UserID":42,"Expired":true},"User":{}}\n'; exit 1
    else
      printf '{"BackendState":"NeedsLogin","Self":{"UserID":0}}\n'; exit 1
    fi ;;
  up)
    if [ -n "$key" ]; then
      [ "$(cat "$key")" = good ] && touch "$state.in"
      printf '{\n  "BackendState": "Running"\n}\n'; exit 0
    fi
    if [ -e "$state.hang" ]; then sleep 30; exit 1; fi
    printf '{\n\t"AuthURL": "https://login.example/a/1",\n\t"BackendState": "NeedsLogin"\n}\n'
    sleep 0.3
    printf '{\n\t"AuthURL": "https://login.example/a/2",\n\t"BackendState": "NeedsLogin"\n}\n'
    sleep 0.3
    touch "$state.in"
    printf '{\n  "BackendState": "Running"\n}\n' ;;
  logout) rm -f "$state.in" ;;
esac
"#;

struct Host {
    child: Child,
    input: Option<ChildStdin>,
    events: mpsc::Receiver<Value>,
    state: PathBuf,
    runtime: PathBuf,
    _temp: Temp,
}

/// A scratch folder under the target folder, removed at the end.
struct Temp(PathBuf);
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn temp() -> Temp {
    let path = std::env::temp_dir().join(format!(
        "korri-tailscale-account-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    let _ = std::fs::remove_dir_all(&path);
    std::fs::create_dir_all(&path).unwrap();
    Temp(path)
}

fn start(prepare: impl FnOnce(&Path, &mut Command)) -> Host {
    let temp = temp();
    let dir = temp.0.clone();
    let cli = dir.join("tailscale");
    std::fs::write(&cli, FAKE_CLI).unwrap();
    std::fs::set_permissions(&cli, std::fs::Permissions::from_mode(0o755)).unwrap();
    let runtime = dir.join("run");
    std::fs::create_dir(&runtime).unwrap();
    let state = dir.join("state");
    let mut command = Command::new(env!("CARGO_BIN_EXE_korri-tailscale-account"));
    command
        .env_clear()
        .env("PATH", std::env::var_os("PATH").unwrap_or_default())
        .env("KORRI_TAILSCALE_CLI", &cli)
        .env("FAKE_STATE", &state)
        .env("RUNTIME_DIRECTORY", &runtime)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped());
    prepare(&dir, &mut command);
    let mut child = command.spawn().unwrap();
    let input = child.stdin.take();
    let output = child.stdout.take().unwrap();
    let (send, events) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(output).lines() {
            let line = line.unwrap();
            send.send(serde_json::from_str(&line).expect(&line))
                .unwrap();
        }
    });
    Host {
        child,
        input,
        events,
        state,
        runtime,
        _temp: temp,
    }
}

impl Host {
    fn send(&mut self, line: &str) {
        let input = self.input.as_mut().unwrap();
        writeln!(input, "{line}").unwrap();
        input.flush().unwrap();
    }

    fn next(&self) -> Value {
        self.events
            .recv_timeout(Duration::from_secs(10))
            .expect("an event")
    }

    fn args(&self) -> String {
        std::fs::read_to_string(self.state.with_extension("args")).unwrap_or_default()
    }

    /// The end of the program's input ends it.
    fn close(mut self) {
        drop(self.input.take());
        let deadline = Instant::now() + Duration::from_secs(5);
        while self.child.try_wait().unwrap().is_none() {
            assert!(Instant::now() < deadline, "the account host did not end");
            std::thread::sleep(Duration::from_millis(20));
        }
    }
}

fn event(name: &str, field: &str, value: &str) -> Value {
    serde_json::json!({"event": name, field: value})
}

#[test]
fn status_says_who_is_signed_in_and_an_expired_key_needs_sign_in() {
    let mut host = start(|_, _| {});
    host.send("status");
    assert_eq!(host.next(), serde_json::json!({"event": "signed_out"}));
    std::fs::write(host.state.with_extension("expired"), "").unwrap();
    host.send("status");
    assert_eq!(host.next(), event("signed_out", "reason", "expired"));
    let socket = format!(
        "--socket={}",
        host.runtime.join("tailscaled.sock").display()
    );
    assert!(
        host.args().lines().all(|line| line.starts_with(&socket)),
        "{}",
        host.args()
    );
    host.close();
}

#[test]
fn signin_qr_shows_each_login_link_then_signs_in_and_signout_ends_it() {
    let mut host = start(|_, _| {});
    host.send("signin-qr");
    assert_eq!(
        host.next(),
        event("qr_code", "challenge_url", "https://login.example/a/1")
    );
    assert_eq!(
        host.next(),
        event("qr_refreshed", "challenge_url", "https://login.example/a/2")
    );
    assert_eq!(
        host.next(),
        event("signed_in", "account_name", "p@example.com")
    );
    assert!(
        host.args()
            .contains("up --json --reset --accept-dns=false --timeout=890s"),
        "{}",
        host.args()
    );
    assert!(!host.args().contains("--auth-key"));
    host.send("status");
    assert_eq!(
        host.next(),
        event("signed_in", "account_name", "p@example.com")
    );
    host.send("signout");
    assert_eq!(host.next(), serde_json::json!({"event": "signed_out"}));
    host.close();
}

#[test]
fn the_admitted_credential_signs_in_with_no_link() {
    let mut host = start(|dir, command| {
        let credentials = dir.join("credentials");
        std::fs::create_dir(&credentials).unwrap();
        std::fs::write(credentials.join("authkey"), "good").unwrap();
        command.env("CREDENTIALS_DIRECTORY", credentials);
    });
    host.send("signin-qr");
    assert_eq!(
        host.next(),
        event("signed_in", "account_name", "p@example.com")
    );
    assert!(host.args().contains("--auth-key=file:"), "{}", host.args());
    assert!(host.args().contains("/credentials/authkey"));
    host.close();
}

#[test]
fn the_end_of_input_ends_a_sign_in_that_waits() {
    let mut host = start(|_, _| {});
    std::fs::write(host.state.with_extension("hang"), "").unwrap();
    host.send("signin-qr");
    std::thread::sleep(Duration::from_millis(300));
    let started = Instant::now();
    host.close();
    assert!(started.elapsed() < Duration::from_secs(5));
}

#[test]
fn without_its_runtime_folder_it_says_so_and_ends() {
    let host = start(|_, command| {
        command.env_remove("RUNTIME_DIRECTORY");
    });
    assert_eq!(
        host.next(),
        event("signin_failed", "reason", "no_runtime_directory")
    );
    host.close();
}

#[test]
fn a_daemon_that_does_not_answer_is_a_failure() {
    let mut host = start(|_, command| {
        command.env("KORRI_TAILSCALE_CLI", "/nonexistent/tailscale");
    });
    host.send("status");
    assert_eq!(
        host.next(),
        event("signin_failed", "reason", "daemon_unreachable")
    );
    host.send("signin-qr");
    assert_eq!(host.next(), event("signin_failed", "reason", "cli_missing"));
    host.close();
}
