//! Steam's own app metadata cache, `appcache/appinfo.vdf`, written by the
//! engine. Ported from the spike's `scripts/mini/steam-launch-entry.py` (format
//! 0x07564429: a header, the app records, then a string table that the binary
//! key/values index into). The host reads only public app metadata here:
//! names, types, launch entries and Steam Cloud rules. No per-game rules.
use std::collections::BTreeMap;

const MAGIC: u32 = 0x0756_4429;
/// Bytes between an app record's size field and its key/values: info state 4,
/// last change 4, PICS token 8, SHA-1 20, change number 4, binary SHA-1 20.
const RECORD_HEADER: usize = 4 + 4 + 8 + 20 + 4 + 20;
const MAX_DEPTH: usize = 64;

/// One binary key/value. Integers keep their value; other number types are
/// kept only as present.
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Object(BTreeMap<String, Value>),
    String(String),
    Int(i64),
    Other,
}
impl Value {
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Object(map) => map.get(key),
            _ => None,
        }
    }
    pub fn path(&self, keys: &[&str]) -> Option<&Value> {
        keys.iter().try_fold(self, |value, key| value.get(key))
    }
    /// A string, or an integer written as a string (appinfo mixes both).
    pub fn text(&self) -> Option<String> {
        match self {
            Value::String(s) => Some(s.clone()),
            Value::Int(i) => Some(i.to_string()),
            _ => None,
        }
    }
    pub fn int(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            Value::String(s) => s.trim().parse().ok(),
            _ => None,
        }
    }
    pub fn entries(&self) -> impl Iterator<Item = (&String, &Value)> {
        match self {
            Value::Object(map) => Some(map.iter()),
            _ => None,
        }
        .into_iter()
        .flatten()
    }
}

/// Every app record of one appinfo.vdf, by appid. Records that fail to parse are
/// skipped; a file in another format gives an error.
pub fn read(bytes: &[u8]) -> Result<BTreeMap<u32, Value>, String> {
    let u32_at = |at: usize| -> Option<u32> {
        Some(u32::from_le_bytes(bytes.get(at..at + 4)?.try_into().ok()?))
    };
    if u32_at(0) != Some(MAGIC) {
        return Err("unsupported appinfo.vdf format".into());
    }
    let table = bytes
        .get(8..16)
        .map(|b| i64::from_le_bytes(b.try_into().unwrap()))
        .filter(|t| *t > 16 && (*t as usize) < bytes.len())
        .ok_or("appinfo.vdf has no string table")? as usize;
    let count = u32_at(table).ok_or("appinfo.vdf string table is cut short")? as usize;
    let mut strings = Vec::with_capacity(count.min(1 << 20));
    let mut at = table + 4;
    for _ in 0..count {
        let end = at + memchr0(&bytes[at.min(bytes.len())..]).ok_or("bad string table")?;
        strings.push(String::from_utf8_lossy(&bytes[at..end]).into_owned());
        at = end + 1;
    }
    let mut apps = BTreeMap::new();
    let mut pos = 16;
    while pos + 8 <= table {
        let appid = u32_at(pos).ok_or("cut short")?;
        if appid == 0 {
            break;
        }
        let size = u32_at(pos + 4).ok_or("cut short")? as usize;
        let start = pos + 8;
        let end = start
            .checked_add(size)
            .filter(|e| *e <= table)
            .ok_or("bad record size")?;
        let mut cursor = start + RECORD_HEADER;
        if cursor < end {
            if let Ok(Value::Object(mut map)) = object(&bytes[..end], &mut cursor, &strings, 0) {
                let app = map.remove("appinfo").unwrap_or(Value::Object(map));
                apps.insert(appid, app);
            }
        }
        pos = end;
    }
    Ok(apps)
}

fn memchr0(bytes: &[u8]) -> Option<usize> {
    bytes.iter().position(|b| *b == 0)
}

fn object(
    buf: &[u8],
    at: &mut usize,
    strings: &[String],
    depth: usize,
) -> Result<Value, &'static str> {
    if depth > MAX_DEPTH {
        return Err("nesting limit");
    }
    let mut map = BTreeMap::new();
    loop {
        let kind = *buf.get(*at).ok_or("cut short")?;
        *at += 1;
        if kind == 8 {
            return Ok(Value::Object(map));
        }
        let index = buf.get(*at..*at + 4).ok_or("cut short")?;
        *at += 4;
        let key = strings
            .get(u32::from_le_bytes(index.try_into().unwrap()) as usize)
            .ok_or("bad key index")?
            .clone();
        let mut fixed = |n: usize| -> Result<&[u8], &'static str> {
            let v = buf.get(*at..*at + n).ok_or("cut short")?;
            *at += n;
            Ok(v)
        };
        let value = match kind {
            0 => object(buf, at, strings, depth + 1)?,
            1 => {
                let end = *at + memchr0(&buf[*at..]).ok_or("cut short")?;
                let v = String::from_utf8_lossy(&buf[*at..end]).into_owned();
                *at = end + 1;
                Value::String(v)
            }
            2 | 4 | 6 => Value::Int(i32::from_le_bytes(fixed(4)?.try_into().unwrap()) as i64),
            3 => {
                fixed(4)?;
                Value::Other
            }
            7 | 10 => Value::Int(u64::from_le_bytes(fixed(8)?.try_into().unwrap()) as i64),
            _ => return Err("unknown value type"),
        };
        map.insert(key, value);
    }
}

/// The app's display name and type, from `common`.
pub fn name_and_type(app: &Value) -> (Option<String>, Option<String>) {
    let common = app.get("common");
    let field = |key| common.and_then(|c| c.get(key)).and_then(Value::text);
    (
        field("name").filter(|n| !n.trim().is_empty()),
        field("type"),
    )
}

#[cfg(test)]
pub mod tests {
    use super::*;

    /// Builds an appinfo.vdf with one app per (appid, key/values) pair.
    pub struct Writer {
        strings: Vec<String>,
    }
    pub enum W<'a> {
        O(Vec<(&'a str, W<'a>)>),
        S(&'a str),
        I(i32),
    }
    impl Writer {
        pub fn file(apps: &[(u32, W)]) -> Vec<u8> {
            let mut writer = Writer { strings: vec![] };
            let mut records = Vec::new();
            for (appid, kv) in apps {
                let mut body = vec![0u8; RECORD_HEADER];
                writer.object(&mut body, kv);
                records.extend_from_slice(&appid.to_le_bytes());
                records.extend_from_slice(&(body.len() as u32).to_le_bytes());
                records.extend_from_slice(&body);
            }
            records.extend_from_slice(&0u32.to_le_bytes());
            let table = 16 + records.len();
            let mut out = Vec::new();
            out.extend_from_slice(&MAGIC.to_le_bytes());
            out.extend_from_slice(&1u32.to_le_bytes());
            out.extend_from_slice(&(table as i64).to_le_bytes());
            out.extend_from_slice(&records);
            out.extend_from_slice(&(writer.strings.len() as u32).to_le_bytes());
            for s in &writer.strings {
                out.extend_from_slice(s.as_bytes());
                out.push(0);
            }
            out
        }
        fn key(&mut self, out: &mut Vec<u8>, key: &str) {
            let index = match self.strings.iter().position(|s| s == key) {
                Some(i) => i,
                None => {
                    self.strings.push(key.into());
                    self.strings.len() - 1
                }
            };
            out.extend_from_slice(&(index as u32).to_le_bytes());
        }
        fn object(&mut self, out: &mut Vec<u8>, value: &W) {
            let W::O(entries) = value else { panic!() };
            for (key, value) in entries {
                match value {
                    W::O(_) => {
                        out.push(0);
                        self.key(out, key);
                        self.object(out, value);
                    }
                    W::S(s) => {
                        out.push(1);
                        self.key(out, key);
                        out.extend_from_slice(s.as_bytes());
                        out.push(0);
                    }
                    W::I(i) => {
                        out.push(2);
                        self.key(out, key);
                        out.extend_from_slice(&i.to_le_bytes());
                    }
                }
            }
            out.push(8);
        }
    }

    #[test]
    fn reads_names_types_and_nested_rules() {
        use W::*;
        let file = Writer::file(&[
            (
                10,
                O(vec![(
                    "appinfo",
                    O(vec![
                        ("common", O(vec![("name", S("Game")), ("type", S("Game"))])),
                        ("ufs", O(vec![("quota", I(1000))])),
                    ]),
                )]),
            ),
            (20, O(vec![("common", O(vec![("type", S("Tool"))]))])),
        ]);
        let apps = read(&file).unwrap();
        assert_eq!(
            name_and_type(&apps[&10]),
            (Some("Game".into()), Some("Game".into()))
        );
        assert_eq!(
            apps[&10].path(&["ufs", "quota"]).and_then(Value::int),
            Some(1000)
        );
        assert_eq!(name_and_type(&apps[&20]), (None, Some("Tool".into())));
    }

    #[test]
    fn refuses_other_formats_and_survives_a_cut_file() {
        assert!(read(b"not appinfo").is_err());
        use W::*;
        let mut file = Writer::file(&[(10, O(vec![("common", O(vec![("name", S("A"))]))]))]);
        file.truncate(30);
        assert!(read(&file).is_err());
    }
}
