//! Which platform's build of an app is installed: the depots the app's
//! manifest (`steamapps/appmanifest_<appid>.acf`, "InstalledDepots") lists,
//! against each depot's `config/oslist` in the engine's appinfo cache. Depots
//! with no oslist are shared by every platform and decide nothing.
//!
//! Device proof (Korri ADR 0083): before the compatibility tool was set the
//! engine installed VVVVVV's Linux depot; the runner plays Windows builds
//! through Proton, so such an install is replaced.
use crate::appinfo::{self, Value};
use std::{collections::BTreeSet, path::Path};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Build {
    /// An installed depot is for Windows.
    Windows,
    /// The installed depots are for other platforms only, and the app has a
    /// Windows depot that is not installed.
    OtherThanWindows,
    /// Not installed, no platform depot, or nothing to compare.
    Unknown,
}

/// The depot ids of the "InstalledDepots" block of an appmanifest.
pub fn installed_depots(manifest: &str) -> BTreeSet<u32> {
    let tokens = tokens(manifest);
    let mut depots = BTreeSet::new();
    let Some(start) = tokens
        .iter()
        .position(|t| t.eq_ignore_ascii_case("InstalledDepots"))
    else {
        return depots;
    };
    if tokens.get(start + 1).map(String::as_str) != Some("{") {
        return depots;
    }
    let mut depth = 0usize;
    let mut i = start + 2;
    while i < tokens.len() {
        match tokens[i].as_str() {
            "{" => depth += 1,
            "}" if depth == 0 => break,
            "}" => depth -= 1,
            key if depth == 0 && tokens.get(i + 1).map(String::as_str) == Some("{") => {
                if let Ok(id) = key.parse() {
                    depots.insert(id);
                }
            }
            _ => {}
        }
        i += 1;
    }
    depots
}

/// Quoted strings and braces of a text VDF (no escapes beyond \" and \\).
fn tokens(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '{' | '}' => out.push(c.to_string()),
            '"' => {
                let mut value = String::new();
                while let Some(c) = chars.next() {
                    match c {
                        '\\' => {
                            if let Some(next) = chars.next() {
                                value.push(next);
                            }
                        }
                        '"' => break,
                        c => value.push(c),
                    }
                }
                out.push(value);
            }
            _ => {}
        }
    }
    out
}

fn oslist(app: &Value, depot: u32) -> Option<BTreeSet<String>> {
    let list = app
        .path(&["depots", &depot.to_string(), "config", "oslist"])
        .and_then(Value::text)?;
    let set: BTreeSet<String> = list
        .split(',')
        .map(|s| s.trim().to_ascii_lowercase())
        .filter(|s| !s.is_empty())
        .collect();
    (!set.is_empty()).then_some(set)
}

/// The platform of the installed build, from the manifest text and the app's
/// appinfo record.
pub fn build_of(manifest: &str, app: &Value) -> Build {
    let installed = installed_depots(manifest);
    let mut installed_platform = false;
    for depot in &installed {
        if let Some(os) = oslist(app, *depot) {
            if os.contains("windows") {
                return Build::Windows;
            }
            installed_platform = true;
        }
    }
    let windows_available =
        app.get("depots")
            .into_iter()
            .flat_map(Value::entries)
            .any(|(id, _)| {
                id.parse()
                    .ok()
                    .and_then(|id| oslist(app, id))
                    .is_some_and(|os| os.contains("windows"))
            });
    if installed_platform && windows_available {
        Build::OtherThanWindows
    } else {
        Build::Unknown
    }
}

/// The installed build of `appid` in the Steam root, read from its manifest
/// and the engine's appinfo cache on disk.
pub fn installed_build(steam: &Path, appid: u32) -> Build {
    let Ok(manifest) =
        std::fs::read_to_string(steam.join(format!("steamapps/appmanifest_{appid}.acf")))
    else {
        return Build::Unknown;
    };
    let Ok(apps) = std::fs::read(steam.join("appcache/appinfo.vdf"))
        .map_err(|_| ())
        .and_then(|bytes| appinfo::read(&bytes).map_err(|_| ()))
    else {
        return Build::Unknown;
    };
    match apps.get(&appid) {
        Some(app) => build_of(&manifest, app),
        None => Build::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::appinfo::Value as V;

    fn object(entries: Vec<(&str, V)>) -> V {
        V::Object(entries.into_iter().map(|(k, v)| (k.into(), v)).collect())
    }
    fn depot(os: Option<&str>) -> V {
        match os {
            Some(os) => object(vec![(
                "config",
                object(vec![("oslist", V::String(os.into()))]),
            )]),
            None => object(vec![]),
        }
    }
    /// VVVVVV's shape: a shared depot, a Windows depot and a Linux depot.
    fn app() -> V {
        object(vec![(
            "depots",
            object(vec![
                ("70301", depot(None)),
                ("70302", depot(Some("windows"))),
                ("70303", depot(Some("linux"))),
            ]),
        )])
    }
    fn manifest(depots: &[u32]) -> String {
        let inner: String = depots
            .iter()
            .map(|d| format!("\t\t\"{d}\"\n\t\t{{\n\t\t\t\"manifest\"\t\t\"1\"\n\t\t\t\"size\"\t\t\"2\"\n\t\t}}\n"))
            .collect();
        format!(
            "\"AppState\"\n{{\n\t\"appid\"\t\t\"70300\"\n\t\"InstalledDepots\"\n\t{{\n{inner}\t}}\n\t\"UserConfig\"\n\t{{\n\t\t\"language\"\t\t\"english\"\n\t}}\n}}\n"
        )
    }

    #[test]
    fn reads_the_installed_depot_ids() {
        assert_eq!(
            installed_depots(&manifest(&[70301, 70303])),
            BTreeSet::from([70301, 70303])
        );
        assert!(installed_depots("\"AppState\" { }").is_empty());
    }

    #[test]
    fn a_linux_build_of_an_app_with_a_windows_build_is_other_than_windows() {
        assert_eq!(
            build_of(&manifest(&[70301, 70303]), &app()),
            Build::OtherThanWindows
        );
        assert_eq!(build_of(&manifest(&[70301, 70302]), &app()), Build::Windows);
        // Only shared depots, or no Windows build at all: nothing to replace.
        assert_eq!(build_of(&manifest(&[70301]), &app()), Build::Unknown);
        let linux_only = object(vec![("depots", object(vec![("1", depot(Some("linux")))]))]);
        assert_eq!(build_of(&manifest(&[1]), &linux_only), Build::Unknown);
        let both = object(vec![(
            "depots",
            object(vec![("1", depot(Some("windows,linux")))]),
        )]);
        assert_eq!(build_of(&manifest(&[1]), &both), Build::Windows);
    }
}
