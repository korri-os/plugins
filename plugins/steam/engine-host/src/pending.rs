//! Pending remote operations at a launch (Core ADR 0083, owner decision
//! 2026-11-21): another device of the account has a session open or a save
//! not uploaded yet, and Steam refuses the launch download until it ends.
//!
//! The engine's `AC Launch,down` job sends `Cloud.SignalAppLaunchIntent`.
//! When Steam answers with pending operations, the job logs them and stops
//! before its download (steamclient.so 1792618285, 0x611c80..0x611fc8). The
//! engine keeps them only in a C++ protobuf object
//! (`GetPendingRemoteOperationInfo` parses into a `CMsgCloudPendingRemoteOperations`
//! the caller must own), which this host cannot build. So the host reads the
//! two lines the job writes to the engine's own `logs/cloud_log.txt`:
//!
//! ```text
//! [2026-11-21 15:32:15] [AppID 584400] BYieldingAppLaunchIntent returned 1 pending remote operations:
//! [2026-11-21 15:32:15] <TAB>Operation '3' from machine ''
//! ```
//!
//! This is fragile by nature: the words are the engine's log format strings
//! (0x20ac2c0 and 0x20ac310), not an interface. The read is bounded, read-only
//! and parses only these two line shapes. It fails closed: a header whose
//! operations cannot be read, or a log that cannot be read at all, is a
//! pending operation of an unknown device, and the person is still asked.
use std::{
    fs::File,
    io::{Read, Seek, SeekFrom},
    path::Path,
};

/// The most bytes read after a mark; the newest bytes win.
const MAX_READ: u64 = 1 << 20;
/// The most operations reported for one launch.
const MAX_OPERATIONS: usize = 8;
/// The most characters of a machine name reported.
const MAX_MACHINE: usize = 64;

/// ECloudPendingRemoteOperation, from the engine's enum descriptor
/// (`k_ECloudPendingRemoteOperation*`).
pub fn operation_name(kind: Option<u32>) -> &'static str {
    match kind {
        Some(0) => "none",
        Some(1) => "app_session_active",
        Some(2) => "upload_in_progress",
        Some(3) => "upload_pending",
        Some(4) => "app_session_suspended",
        _ => "unknown",
    }
}

/// One operation as the engine logged it. `None` is what the log did not say.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Operation {
    pub kind: Option<u32>,
    /// The other device's name; `None` when Steam sent an empty one.
    pub machine: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Found {
    /// The launch intent reported nothing pending for the app.
    Nothing,
    /// At least one operation; an empty list when the log could not be read.
    Pending(Vec<Operation>),
}

/// Where the log ended when the launch download was asked for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Mark(u64);

pub fn mark(log: &Path) -> Mark {
    Mark(std::fs::metadata(log).map_or(0, |m| m.len()))
}

/// What the engine logged for `appid` after `mark`. The engine rotates the log
/// to `cloud_log.previous.txt`; a log shorter than the mark was rotated.
pub fn probe(log: &Path, previous: &Path, mark: Mark, appid: u32) -> Found {
    let current = match std::fs::metadata(log) {
        Ok(meta) => meta.len(),
        Err(_) => return Found::Pending(Vec::new()),
    };
    let text = if current >= mark.0 {
        read_from(log, mark.0)
    } else {
        // Rotated: the rest of the old file, then the new one.
        read_from(previous, mark.0).and_then(|mut old| {
            read_from(log, 0).map(|new| {
                old.push_str(&new);
                old
            })
        })
    };
    match text {
        Some(text) => find(&text, appid),
        None => Found::Pending(Vec::new()),
    }
}

fn read_from(path: &Path, from: u64) -> Option<String> {
    let mut file = File::open(path).ok()?;
    let len = file.metadata().ok()?.len();
    let start = from.max(len.saturating_sub(MAX_READ)).min(len);
    file.seek(SeekFrom::Start(start)).ok()?;
    let mut bytes = Vec::new();
    file.take(MAX_READ).read_to_end(&mut bytes).ok()?;
    Some(String::from_utf8_lossy(&bytes).into_owned())
}

/// The text after the log line's `[date time] ` stamp.
fn message(line: &str) -> &str {
    match line
        .strip_prefix('[')
        .and_then(|rest| rest.split_once("] "))
    {
        Some((_, message)) => message,
        None => line,
    }
}

/// The newest launch-intent report for `appid` in `text`.
pub fn find(text: &str, appid: u32) -> Found {
    let header = format!("[AppID {appid}] BYieldingAppLaunchIntent returned ");
    let lines: Vec<&str> = text.lines().collect();
    let Some((at, count)) = lines.iter().enumerate().rev().find_map(|(at, line)| {
        let rest = message(line).strip_prefix(header.as_str())?;
        let count = rest
            .strip_suffix(" pending remote operations:")
            .and_then(|n| n.parse::<usize>().ok());
        Some((at, count))
    }) else {
        return Found::Nothing;
    };
    match count {
        Some(0) => return Found::Nothing,
        // A header that does not parse is still a report: ask.
        None => return Found::Pending(vec![unknown()]),
        Some(_) => {}
    }
    let count = count.unwrap_or(1).min(MAX_OPERATIONS);
    // Other threads may write between the header and its operation lines.
    let mut operations: Vec<Operation> = lines[at + 1..]
        .iter()
        .take(count + 16)
        .filter_map(|line| operation(message(line)))
        .take(count)
        .collect();
    while operations.len() < count {
        operations.push(unknown());
    }
    Found::Pending(operations)
}

fn unknown() -> Operation {
    Operation {
        kind: None,
        machine: None,
    }
}

/// `\tOperation '3' from machine 'zao'`; the name may hold quotes itself.
fn operation(message: &str) -> Option<Operation> {
    let rest = message
        .trim_start_matches('\t')
        .strip_prefix("Operation '")?;
    let (kind, rest) = rest.split_once("' from machine '")?;
    let machine = rest.strip_suffix('\'')?;
    let machine: String = machine
        .chars()
        .filter(|c| !c.is_control())
        .take(MAX_MACHINE)
        .collect();
    let machine = machine.trim();
    Some(Operation {
        kind: kind.parse().ok(),
        machine: (!machine.is_empty()).then(|| machine.to_owned()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Lines from the op6's cloud_log.txt, 2026-11-21 (Sonic Mania).
    const REFUSED: &str = "[2026-11-21 15:32:15] [AppID 584400] Need to download file SaveData.bin
[2026-11-21 15:32:15] [AppID 584400] BYieldingAppLaunchIntent returned 1 pending remote operations:
[2026-11-21 15:32:15] \tOperation '3' from machine ''
[2026-11-21 15:32:15] [AppID 584400] YldWriteCacheDirectoryToFile - saved to 'x'
";

    #[test]
    fn a_launch_intent_report_names_each_operation_and_its_device() {
        assert_eq!(
            find(REFUSED, 584400),
            Found::Pending(vec![Operation {
                kind: Some(3),
                machine: None
            }])
        );
        assert_eq!(operation_name(Some(3)), "upload_pending");
        let two = "[t] [AppID 7] BYieldingAppLaunchIntent returned 2 pending remote operations:
[t] [AppID 9] unrelated
[t] \tOperation '1' from machine 'Living room'
[t] \tOperation '2' from machine 'Bob's Deck'
";
        assert_eq!(
            find(two, 7),
            Found::Pending(vec![
                Operation {
                    kind: Some(1),
                    machine: Some("Living room".into())
                },
                Operation {
                    kind: Some(2),
                    machine: Some("Bob's Deck".into())
                },
            ])
        );
    }

    #[test]
    fn nothing_pending_is_nothing_and_other_apps_do_not_count() {
        assert_eq!(find(REFUSED, 275200), Found::Nothing);
        assert_eq!(find("", 1), Found::Nothing);
        assert_eq!(
            find(
                "[t] [AppID 1] BYieldingAppLaunchIntent returned 0 pending remote operations:\n",
                1
            ),
            Found::Nothing
        );
        // A failed request is no pending operation.
        assert_eq!(
            find(
                "[t] [AppID 1] BYieldingAppLaunchIntent Failed with 'Timeout' (16)\n",
                1
            ),
            Found::Nothing
        );
    }

    #[test]
    fn what_cannot_be_read_still_asks_with_an_unknown_device() {
        // Operation lines missing or in another shape.
        assert_eq!(
            find(
                "[t] [AppID 1] BYieldingAppLaunchIntent returned 2 pending remote operations:\n[t] \tOperation 3 from zao\n",
                1
            ),
            Found::Pending(vec![unknown(), unknown()])
        );
        // A header whose count does not parse.
        assert_eq!(
            find(
                "[t] [AppID 1] BYieldingAppLaunchIntent returned many pending remote operations:\n",
                1
            ),
            Found::Pending(vec![unknown()])
        );
        let dir = std::env::temp_dir().join(format!("korri-pending-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let log = dir.join("cloud_log.txt");
        let previous = dir.join("cloud_log.previous.txt");
        assert_eq!(probe(&log, &previous, Mark(0), 1), Found::Pending(vec![]));
        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn only_lines_after_the_mark_count_also_across_a_rotation() {
        let dir = std::env::temp_dir().join(format!("korri-pending-r-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let log = dir.join("cloud_log.txt");
        let previous = dir.join("cloud_log.previous.txt");
        std::fs::write(&log, REFUSED).unwrap();
        let at = mark(&log);
        assert_eq!(probe(&log, &previous, at, 584400), Found::Nothing);
        let mut text = REFUSED.to_owned();
        text.push_str(REFUSED);
        std::fs::write(&log, &text).unwrap();
        assert!(matches!(
            probe(&log, &previous, at, 584400),
            Found::Pending(_)
        ));
        // Rotated: the old file holds the report, the new one is short.
        std::fs::write(&previous, &text).unwrap();
        std::fs::write(&log, "[t] [AppID 5] x\n").unwrap();
        assert!(matches!(
            probe(&log, &previous, at, 584400),
            Found::Pending(_)
        ));
        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn a_machine_name_is_one_short_line() {
        let long = format!("[t] \tOperation '3' from machine '{}'", "x".repeat(200));
        let op = operation(message(&long)).unwrap();
        assert_eq!(op.machine.map(|m| m.len()), Some(MAX_MACHINE));
        let op = operation("\tOperation '3' from machine 'a\u{7}b'").unwrap();
        assert_eq!(op.machine.as_deref(), Some("ab"));
    }
}
