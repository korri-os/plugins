//! Steam's QR login (ADR 0083, route B of the spike's results/qr/README.md),
//! done by the host over Steam's public web API, as SteamKit2 and
//! node-steam-session do. The pinned engine has no QR call of its own.
//!
//! Field numbers come from the engine's own descriptor of
//! steammessages_auth.steamclient.proto (spike scripts/qr/aka/qr-descriptor.py).
//! The refresh token stays in this process: it is never printed, logged or
//! written. The host hands it to the engine (IClientUser::SetLoginToken) and
//! then overwrites its own copies. The access token in the poll reply is never
//! kept. The challenge URL is the QR payload; it is not a secret and is reported.
use std::{
    io::Read,
    thread,
    time::{Duration, Instant},
};

const API: &str = "https://api.steampowered.com/IAuthenticationService";
/// EAuthTokenPlatformType k_EAuthTokenPlatformType_SteamClient (descriptor).
const PLATFORM_STEAM_CLIENT: u64 = 1;
/// EOSType k_EOSTypeLinuxUnknown (prior art); only shown to the person.
const OS_LINUX_UNKNOWN: i64 = -203;
/// EResult values in the x-eresult header.
const ERESULT_OK: i32 = 1;

/// Bytes that are overwritten with zeros when dropped.
pub struct Secret(pub Vec<u8>);
impl Drop for Secret {
    fn drop(&mut self) {
        wipe(&mut self.0);
    }
}
pub fn wipe(bytes: &mut [u8]) {
    for b in bytes.iter_mut() {
        // SAFETY: b is a valid, aligned &mut u8.
        unsafe { std::ptr::write_volatile(b, 0) };
    }
}

// --- protobuf, the few wire forms these messages use ---------------------------
fn varint(out: &mut Vec<u8>, mut v: u64) {
    loop {
        let b = (v & 0x7f) as u8;
        v >>= 7;
        if v == 0 {
            out.push(b);
            return;
        }
        out.push(b | 0x80);
    }
}
fn tag(out: &mut Vec<u8>, field: u64, wire: u64) {
    varint(out, field << 3 | wire);
}
fn bytes_field(out: &mut Vec<u8>, field: u64, value: &[u8]) {
    tag(out, field, 2);
    varint(out, value.len() as u64);
    out.extend_from_slice(value);
}
fn number_field(out: &mut Vec<u8>, field: u64, value: u64) {
    tag(out, field, 0);
    varint(out, value);
}

#[derive(Debug, PartialEq)]
pub enum Value<'a> {
    Varint(u64),
    Bytes(&'a [u8]),
    Fixed32([u8; 4]),
    Fixed64([u8; 8]),
}
fn read_varint(buf: &[u8], pos: &mut usize) -> Option<u64> {
    let mut value = 0u64;
    for shift in (0..64).step_by(7) {
        let b = *buf.get(*pos)?;
        *pos += 1;
        value |= u64::from(b & 0x7f) << shift;
        if b < 0x80 {
            return Some(value);
        }
    }
    None
}
pub fn parse(buf: &[u8]) -> Option<Vec<(u64, Value<'_>)>> {
    let mut pos = 0;
    let mut fields = Vec::new();
    while pos < buf.len() {
        let key = read_varint(buf, &mut pos)?;
        let value = match key & 7 {
            0 => Value::Varint(read_varint(buf, &mut pos)?),
            1 => {
                let v = buf.get(pos..pos + 8)?.try_into().ok()?;
                pos += 8;
                Value::Fixed64(v)
            }
            2 => {
                let len = read_varint(buf, &mut pos)? as usize;
                let v = buf.get(pos..pos.checked_add(len)?)?;
                pos += len;
                Value::Bytes(v)
            }
            5 => {
                let v = buf.get(pos..pos + 4)?.try_into().ok()?;
                pos += 4;
                Value::Fixed32(v)
            }
            _ => return None,
        };
        fields.push((key >> 3, value));
    }
    Some(fields)
}

/// CAuthentication_BeginAuthSessionViaQR_Request: 1 device_friendly_name,
/// 2 platform_type, 3 device_details (1 name, 2 platform, 3 os_type,
/// 4 gaming_device_type), 4 website_id.
pub fn begin_request(device_name: &str) -> Vec<u8> {
    let mut details = Vec::new();
    bytes_field(&mut details, 1, device_name.as_bytes());
    number_field(&mut details, 2, PLATFORM_STEAM_CLIENT);
    number_field(&mut details, 3, OS_LINUX_UNKNOWN as u64);
    number_field(&mut details, 4, 1);
    let mut out = Vec::new();
    bytes_field(&mut out, 1, device_name.as_bytes());
    number_field(&mut out, 2, PLATFORM_STEAM_CLIENT);
    bytes_field(&mut out, 3, &details);
    bytes_field(&mut out, 4, b"Client");
    out
}
/// CAuthentication_PollAuthSessionStatus_Request: 1 client_id, 2 request_id.
pub fn poll_request(client_id: u64, request_id: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    number_field(&mut out, 1, client_id);
    bytes_field(&mut out, 2, request_id);
    out
}

#[derive(Debug, Default, PartialEq)]
pub struct Begin {
    pub client_id: u64,
    pub challenge_url: String,
    pub request_id: Vec<u8>,
    pub interval: f32,
}
/// CAuthentication_BeginAuthSessionViaQR_Response: 1 client_id, 2 challenge_url,
/// 3 request_id, 4 interval (float).
pub fn parse_begin(buf: &[u8]) -> Option<Begin> {
    let mut begin = Begin::default();
    for (field, value) in parse(buf)? {
        match (field, value) {
            (1, Value::Varint(v)) => begin.client_id = v,
            (2, Value::Bytes(v)) => begin.challenge_url = String::from_utf8(v.to_vec()).ok()?,
            (3, Value::Bytes(v)) => begin.request_id = v.to_vec(),
            (4, Value::Fixed32(v)) => begin.interval = f32::from_le_bytes(v),
            _ => {}
        }
    }
    (begin.client_id != 0 && !begin.request_id.is_empty() && !begin.challenge_url.is_empty())
        .then_some(begin)
}

#[derive(Default)]
pub struct Poll {
    pub new_client_id: Option<u64>,
    pub new_challenge_url: Option<String>,
    pub refresh_token: Option<Secret>,
    pub had_remote_interaction: bool,
    pub account_name: Option<String>,
}
/// CAuthentication_PollAuthSessionStatus_Response: 1 new_client_id,
/// 2 new_challenge_url, 3 refresh_token, 4 access_token (ignored, never kept),
/// 5 had_remote_interaction, 6 account_name.
pub fn parse_poll(buf: &[u8]) -> Option<Poll> {
    let mut poll = Poll::default();
    for (field, value) in parse(buf)? {
        match (field, value) {
            (1, Value::Varint(v)) => poll.new_client_id = Some(v),
            (2, Value::Bytes(v)) => poll.new_challenge_url = String::from_utf8(v.to_vec()).ok(),
            (3, Value::Bytes(v)) if !v.is_empty() => poll.refresh_token = Some(Secret(v.to_vec())),
            (5, Value::Varint(v)) => poll.had_remote_interaction = v != 0,
            (6, Value::Bytes(v)) => poll.account_name = String::from_utf8(v.to_vec()).ok(),
            _ => {}
        }
    }
    Some(poll)
}

fn base64(input: &[u8]) -> String {
    const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in input.chunks(3) {
        let n = chunk
            .iter()
            .enumerate()
            .fold(0u32, |n, (i, b)| n | u32::from(*b) << (16 - 8 * i));
        for i in 0..4 {
            if i <= chunk.len() {
                out.push(T[(n >> (18 - 6 * i) & 63) as usize] as char);
            } else {
                out.push('=');
            }
        }
    }
    out
}

/// One IAuthenticationService call. Returns (x-eresult, body). The body may hold
/// the refresh token, so it is returned as a Secret.
fn call(agent: &ureq::Agent, method: &str, body: &[u8]) -> Result<(i32, Secret), CallError> {
    let url = format!("{API}/{method}/v1");
    let encoded = base64(body);
    let response = match agent
        .post(&url)
        .send_form(&[("input_protobuf_encoded", encoded.as_str())])
    {
        Ok(r) => r,
        Err(ureq::Error::Status(code, r)) => {
            let eresult = r
                .header("x-eresult")
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            let message = format!("{method}: HTTP {code}, EResult {eresult}");
            return Err(CallError {
                retry: code >= 500 || code == 429,
                message,
            });
        }
        Err(e) => {
            return Err(CallError {
                retry: true,
                message: format!("{method}: transport error: {}", e.kind()),
            })
        }
    };
    let eresult = response
        .header("x-eresult")
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    let mut buf = Secret(Vec::new());
    response
        .into_reader()
        .take(1 << 16)
        .read_to_end(&mut buf.0)
        .map_err(|_| CallError {
            retry: true,
            message: format!("{method}: cannot read the reply"),
        })?;
    Ok((eresult, buf))
}

#[derive(Debug)]
pub struct CallError {
    retry: bool,
    message: String,
}
/// Steam's API answered 5xx during its Tuesday maintenance (results/qr). A call
/// that fails that way is repeated every RETRY_WAIT, at most RETRY_LIMIT times.
const RETRY_WAIT: Duration = Duration::from_secs(3);
const RETRY_LIMIT: u32 = 40;
fn call_retrying(
    agent: &ureq::Agent,
    method: &str,
    body: &[u8],
    stop: &dyn Fn() -> bool,
    report: &mut dyn FnMut(Report) -> Result<(), String>,
) -> Result<(i32, Secret), Failure> {
    let mut attempt = 0;
    loop {
        match call(agent, method, body) {
            Ok(reply) => return Ok(reply),
            Err(e) if e.retry && attempt < RETRY_LIMIT => {
                attempt += 1;
                report(Report::Line(&format!(
                    r#"{{"event":"qr_api_retry","method":"{method}","attempt":{attempt},"error":"{}"}}"#,
                    e.message.replace(['"', '\\'], "'")
                )))
                .map_err(|m| Failure::new("output", m))?;
                let until = Instant::now() + RETRY_WAIT;
                while Instant::now() < until {
                    if stop() {
                        return Err(Failure::new("stopped", "stopped during QR sign-in"));
                    }
                    thread::sleep(Duration::from_millis(100));
                }
            }
            Err(e) if e.retry => return Err(Failure::new("steam_unavailable", e.message)),
            Err(e) => return Err(Failure::new("steam_error", e.message)),
        }
    }
}

/// What the flow reports while it runs.
pub enum Report<'a> {
    /// A QR payload to show. `first` is true for the first one of the sign-in.
    Challenge { url: &'a str, first: bool },
    /// One JSON event line with no token and no URL.
    Line(&'a str),
}

/// Why the flow ended without an approval. `reason` is the word korrid gets in
/// `signin_failed`; `message` is for stderr.
#[derive(Debug)]
pub struct Failure {
    pub reason: &'static str,
    pub message: String,
}
impl Failure {
    fn new(reason: &'static str, message: impl Into<String>) -> Self {
        Failure {
            reason,
            message: message.into(),
        }
    }
}

pub struct Approved {
    pub refresh_token: Secret,
    pub account_name: String,
}

/// Runs the QR flow until the person approves it in the Steam mobile app or the
/// time limit ends. A challenge that expires is replaced by a new one.
/// `report` gets each QR payload and one JSON line per step; no line holds a token.
pub fn sign_in(
    device_name: &str,
    limit: Duration,
    stop: &dyn Fn() -> bool,
    report: &mut dyn FnMut(Report) -> Result<(), String>,
) -> Result<Approved, Failure> {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(20))
        .build();
    let started = Instant::now();
    let mut challenges = 0;
    let output = |m: String| Failure::new("output", m);
    'session: loop {
        if started.elapsed() >= limit {
            return Err(Failure::new("timeout", "QR sign-in timed out"));
        }
        let (eresult, body) = call_retrying(
            &agent,
            "BeginAuthSessionViaQR",
            &begin_request(device_name),
            stop,
            report,
        )?;
        if eresult != ERESULT_OK {
            return Err(Failure::new(
                "steam_error",
                format!("BeginAuthSessionViaQR: EResult {eresult}"),
            ));
        }
        let begin = parse_begin(&body.0)
            .ok_or_else(|| Failure::new("steam_error", "BeginAuthSessionViaQR: bad reply"))?;
        let mut client_id = begin.client_id;
        let interval = Duration::from_secs_f32(begin.interval.clamp(1.0, 30.0));
        challenges += 1;
        report(Report::Challenge {
            url: &begin.challenge_url,
            first: challenges == 1,
        })
        .map_err(output)?;
        let mut scanned = false;
        loop {
            let wait_until = Instant::now() + interval;
            while Instant::now() < wait_until {
                if stop() {
                    return Err(Failure::new("stopped", "stopped during QR sign-in"));
                }
                thread::sleep(Duration::from_millis(100));
            }
            if started.elapsed() >= limit {
                continue 'session;
            }
            let (eresult, body) = call_retrying(
                &agent,
                "PollAuthSessionStatus",
                &poll_request(client_id, &begin.request_id),
                stop,
                report,
            )?;
            if eresult != ERESULT_OK {
                // The session expired or was declined: start a new one.
                report(Report::Line(&format!(
                    r#"{{"event":"qr_session_ended","eresult":{eresult},"seconds":{:.1}}}"#,
                    started.elapsed().as_secs_f32()
                )))
                .map_err(output)?;
                continue 'session;
            }
            let poll = parse_poll(&body.0)
                .ok_or_else(|| Failure::new("steam_error", "PollAuthSessionStatus: bad reply"))?;
            drop(body);
            if let Some(id) = poll.new_client_id {
                client_id = id;
            }
            if let Some(url) = poll.new_challenge_url.as_deref().filter(|u| !u.is_empty()) {
                challenges += 1;
                report(Report::Challenge { url, first: false }).map_err(output)?;
            }
            if poll.had_remote_interaction && !scanned {
                scanned = true;
                report(Report::Line(&format!(
                    r#"{{"event":"qr_scanned","seconds":{:.1}}}"#,
                    started.elapsed().as_secs_f32()
                )))
                .map_err(output)?;
            }
            if let Some(refresh_token) = poll.refresh_token {
                let account_name =
                    poll.account_name.filter(|a| !a.is_empty()).ok_or_else(|| {
                        Failure::new(
                            "steam_error",
                            "PollAuthSessionStatus: approved, but no account name",
                        )
                    })?;
                report(Report::Line(&format!(
                    r#"{{"event":"qr_approved","challenges":{challenges},"seconds":{:.1}}}"#,
                    started.elapsed().as_secs_f32()
                )))
                .map_err(output)?;
                return Ok(Approved {
                    refresh_token,
                    account_name,
                });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn begin_request_matches_the_engine_descriptor() {
        let b = begin_request("K");
        let fields = parse(&b).unwrap();
        assert_eq!(fields[0], (1, Value::Bytes(b"K")));
        assert_eq!(fields[1], (2, Value::Varint(1)));
        let Value::Bytes(details) = fields[2].1 else {
            panic!()
        };
        assert_eq!(fields[2].0, 3);
        let d = parse(details).unwrap();
        assert_eq!(d[1], (2, Value::Varint(1)));
        assert_eq!(d[2], (3, Value::Varint((-203i64) as u64)));
        assert_eq!(fields[3], (4, Value::Bytes(b"Client")));
    }

    #[test]
    fn parse_begin_reads_the_reply() {
        let mut r = Vec::new();
        number_field(&mut r, 1, 77);
        bytes_field(&mut r, 2, b"https://s.team/q/1/x");
        bytes_field(&mut r, 3, &[1, 2, 3]);
        tag(&mut r, 4, 5);
        r.extend_from_slice(&5.0f32.to_le_bytes());
        bytes_field(&mut r, 5, &[8, 4]);
        number_field(&mut r, 6, 1);
        let b = parse_begin(&r).unwrap();
        assert_eq!(b.client_id, 77);
        assert_eq!(b.request_id, vec![1, 2, 3]);
        assert_eq!(b.interval, 5.0);
        assert!(parse_begin(&[]).is_none());
    }

    #[test]
    fn parse_poll_keeps_the_token_out_of_debug_output() {
        let mut r = Vec::new();
        bytes_field(&mut r, 3, b"secret");
        bytes_field(&mut r, 4, b"access");
        number_field(&mut r, 5, 1);
        bytes_field(&mut r, 6, b"name");
        let p = parse_poll(&r).unwrap();
        assert_eq!(p.refresh_token.as_ref().unwrap().0, b"secret");
        assert!(p.had_remote_interaction);
        assert_eq!(p.account_name.as_deref(), Some("name"));
        let empty = parse_poll(&[]).unwrap();
        assert!(empty.refresh_token.is_none());
    }

    #[test]
    fn base64_matches_rfc4648() {
        assert_eq!(base64(b""), "");
        assert_eq!(base64(b"f"), "Zg==");
        assert_eq!(base64(b"fo"), "Zm8=");
        assert_eq!(base64(b"foo"), "Zm9v");
        assert_eq!(base64(b"foobar"), "Zm9vYmFy");
        assert_eq!(base64(&[0xfb, 0xff]), "+/8=");
    }

    /// Live check against Steam (aka only, `cargo test -- --ignored`): a new QR
    /// session that nobody scans. Prints no id.
    #[test]
    #[ignore]
    fn live_begin_and_first_poll() {
        let agent = ureq::AgentBuilder::new()
            .timeout(Duration::from_secs(20))
            .build();
        let (eresult, body) = call(
            &agent,
            "BeginAuthSessionViaQR",
            &begin_request("Korri test"),
        )
        .unwrap();
        assert_eq!(eresult, 1);
        let begin = parse_begin(&body.0).unwrap();
        assert!(begin.challenge_url.starts_with("https://s.team/q/"));
        assert_eq!(begin.request_id.len(), 16);
        let (eresult, body) = call(
            &agent,
            "PollAuthSessionStatus",
            &poll_request(begin.client_id, &begin.request_id),
        )
        .map_err(|e| e.message)
        .unwrap();
        assert_eq!(eresult, 1);
        let poll = parse_poll(&body.0).unwrap();
        assert!(poll.refresh_token.is_none());
        assert!(!poll.had_remote_interaction);
    }

    #[test]
    fn wipe_zeroes() {
        let mut s = Secret(b"abc".to_vec());
        wipe(&mut s.0);
        assert_eq!(s.0, vec![0, 0, 0]);
    }
}
