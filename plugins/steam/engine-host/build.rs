// Export `kill` from the executable, so the dlopened steamclient.so binds its
// kill@plt to the host's PID-namespace translation (main.rs, `kill`).
//
// Engine map (ADR 0083): every steamclient.so address the host checks or calls
// comes from the map that the private remap pipeline writes on aka. The Nix
// build passes it as KORRI_STEAM_ENGINE_MAP (flake input `steam-engine-map`);
// a plain cargo build reads map/engine.map. This script turns it into
// $OUT_DIR/engine_map.rs.
//
// The public map (map/engine.map) is empty: `status missing`. A host built from
// it has ENGINE_MAP_PRESENT = false, every address 0, and reports
// `engine_map_missing` at start without loading the engine. Any other map must be
// a remap map with `status pass` and every entry the host needs, or the build stops.
use std::collections::HashMap;
use std::fmt::Write as _;
use std::path::PathBuf;

/// (generated constant, map key) for the IClientEngine slots the host checks.
const ENGINE: &[(&str, &str)] = &[
    (
        "ENGINE_CREATE_STEAM_PIPE",
        "slot IClientEngine CreateSteamPipe",
    ),
    (
        "ENGINE_RELEASE_STEAM_PIPE",
        "slot IClientEngine BReleaseSteamPipe",
    ),
    (
        "ENGINE_CREATE_GLOBAL_USER",
        "slot IClientEngine CreateGlobalUser",
    ),
    (
        "ENGINE_CONNECT_TO_GLOBAL_USER",
        "slot IClientEngine ConnectToGlobalUser",
    ),
    ("ENGINE_RELEASE_USER", "slot IClientEngine ReleaseUser"),
    ("ENGINE_GET_USER", "slot IClientEngine GetIClientUser"),
    ("ENGINE_RUN_FRAME", "slot IClientEngine RunFrame"),
    (
        "ENGINE_GET_REMOTE_STORAGE",
        "slot IClientEngine GetIClientRemoteStorage",
    ),
    (
        "ENGINE_GET_APP_MANAGER",
        "slot IClientEngine GetIClientAppManager",
    ),
    (
        "ENGINE_SET_COMMAND_LINE",
        "slot IClientEngine SetClientCommandLine",
    ),
    ("ENGINE_GET_COMPAT", "slot IClientEngine GetIClientCompat"),
];
/// IClientUser methods: (constant, method). Proxy table IClientUserMap; the
/// CUser table (IClientUser.CUser) is optional: without it the host accepts
/// only the IPC proxy, which is what GetIClientUser returns (remap evidence).
const USER: &[(&str, &str)] = &[
    ("USER_LOG_ON", "LogOn"),
    ("USER_LOG_OFF", "LogOff"),
    ("USER_LOGGED_ON", "BLoggedOn"),
    ("USER_LOGON_STATE", "GetLogonState"),
    ("USER_CONNECTED", "BConnected"),
    ("USER_STEAM_ID", "GetSteamID"),
    ("USER_HAS_CACHED_CREDENTIALS", "BHasCachedCredentials"),
    (
        "USER_SELECT_CACHED_ACCOUNT",
        "SetAccountNameForCachedCredentialLogin",
    ),
    ("USER_CAN_LOGON_OFFLINE", "CanLogonOffline"),
    ("USER_LOGON_OFFLINE", "LogOnOffline"),
    // QR sign-in hands the refresh token to the engine (spike results/qr).
    ("USER_SET_LOGIN_TOKEN", "SetLoginToken"),
    // list-apps: uint32 GetSubscribedApps(AppId_t *list, uint32 max, bool includeFree).
    ("USER_GET_SUBSCRIBED_APPS", "GetSubscribedApps"),
];
const REMOTE_STORAGE: &[(&str, &str)] = &[
    ("IS_CLOUD_ENABLED_FOR_ACCOUNT", "IsCloudEnabledForAccount"),
    ("IS_CLOUD_ENABLED_FOR_APP", "IsCloudEnabledForApp"),
    ("LOAD_LOCAL_FILE_INFO_CACHE", "LoadLocalFileInfoCache"),
    ("EVALUATE_SYNC_STATE", "EvaluateRemoteStorageSyncState"),
    ("GET_SYNC_STATE", "GetRemoteStorageSyncState"),
    (
        "GET_CONFLICTING_FILE_TIMESTAMPS",
        "GetConflictingFileTimestamps",
    ),
    ("SYNCHRONIZE_APP", "SynchronizeApp"),
    ("IS_APP_SYNC_IN_PROGRESS", "IsAppSyncInProgress"),
    ("RUN_AUTOCLOUD_ON_LAUNCH", "RunAutoCloudOnAppLaunch"),
    ("RUN_AUTOCLOUD_ON_EXIT", "RunAutoCloudOnAppExit"),
    // resolve: bool ResolveSyncConflict(AppId_t, bool acceptLocal) (FINDINGS section 7).
    ("RESOLVE_SYNC_CONFLICT", "ResolveSyncConflict"),
];
const APP_MANAGER: &[(&str, &str)] = &[
    ("INSTALL_APP", "InstallApp"),
    ("UNINSTALL_APP", "UninstallApp"),
    ("GET_APP_INSTALL_STATE", "GetAppInstallState"),
    ("GET_UPDATE_INFO", "GetUpdateInfo"),
    ("IS_APP_UP_TO_DATE", "BIsAppUpToDate"),
    ("IS_DOWNLOADING_ENABLED", "BIsDownloadingEnabled"),
    ("GET_DOWNLOADING_APP_ID", "GetDownloadingAppID"),
    (
        "GET_NUM_APPS_IN_DOWNLOAD_QUEUE",
        "GetNumAppsInDownloadQueue",
    ),
];

/// IClientCompat (IPC proxy): the per-app compatibility tool and with it the
/// engine's platform override, as Steam's own client sets it.
const COMPAT: &[(&str, &str)] = &[
    ("COMPAT_LAYER_ENABLED", "BIsCompatLayerEnabled"),
    ("SPECIFY_COMPAT_TOOL", "SpecifyCompatTool"),
    ("COMPAT_TOOL_ENABLED", "BIsCompatibilityToolEnabled"),
    ("GET_COMPAT_TOOL_NAME", "GetCompatToolName"),
];

fn main() {
    println!("cargo:rustc-link-arg-bins=-Wl,--export-dynamic-symbol=kill");
    println!("cargo:rerun-if-env-changed=KORRI_STEAM_ENGINE_MAP");
    let path = std::env::var_os("KORRI_STEAM_ENGINE_MAP")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("map/engine.map")
        });
    println!("cargo:rerun-if-changed={}", path.display());
    let text = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("engine map {}: {e}", path.display()));
    let out = PathBuf::from(std::env::var_os("OUT_DIR").unwrap()).join("engine_map.rs");
    std::fs::write(
        &out,
        generate(&text).unwrap_or_else(|e| panic!("engine map {}: {e}", path.display())),
    )
    .unwrap();
}

/// Map lines are `<kind> <name> <value...>`, or `slot <table> <method> <index> <rva>`.
fn generate(text: &str) -> Result<String, String> {
    let mut map: HashMap<String, Vec<&str>> = HashMap::new();
    for line in text
        .lines()
        .filter(|l| !l.starts_with('#') && !l.trim().is_empty())
    {
        let t: Vec<&str> = line.split_whitespace().collect();
        let (key, value) = match t.as_slice() {
            ["slot", table, method, rest @ ..] => (format!("slot {table} {method}"), rest.to_vec()),
            [kind, name, rest @ ..] => (format!("{kind} {name}"), rest.to_vec()),
            _ => return Err(format!("bad line: {line}")),
        };
        map.insert(key, value);
    }
    let one = |key: &str| -> Result<&str, String> {
        match map.get(key).map(Vec::as_slice) {
            Some([v]) => Ok(*v),
            _ => Err(format!("missing or malformed `{key}`")),
        }
    };
    if one("format korri-steam-engine-map")? != "1" {
        return Err("not a version 1 korri-steam engine map".into());
    }
    if map.contains_key("status missing") {
        return Ok(missing());
    }
    // `status pass` parses as kind "status", name "pass", no value.
    if !map.contains_key("status pass") {
        return Err("the map's status is not `pass`: remap refused an item".into());
    }
    let hex = |s: &str| usize::from_str_radix(s, 16).map_err(|_| format!("not a hex RVA: {s}"));
    let slot = |key: &str| -> Result<(usize, usize), String> {
        match map.get(key).map(Vec::as_slice) {
            Some([i, rva]) => Ok((
                i.parse().map_err(|_| format!("bad index in `{key}`"))?,
                hex(rva)?,
            )),
            _ => Err(format!("missing `{key}`")),
        }
    };
    let mut rs = String::new();
    writeln!(rs, "pub const ENGINE_MAP_PRESENT: bool = true;").unwrap();
    let sha = one("engine sha256")?;
    writeln!(
        rs,
        "// Generated by build.rs from the engine map; do not edit."
    )
    .unwrap();
    writeln!(
        rs,
        "/// sha256 of the steamclient.so this map was derived from."
    )
    .unwrap();
    writeln!(rs, "pub const ENGINE_SHA256: &str = {sha:?};").unwrap();
    let version = map
        .get("engine client_version")
        .and_then(|v| v.first().copied())
        .unwrap_or("");
    writeln!(rs, "pub const ENGINE_CLIENT_VERSION: &str = {version:?};").unwrap();
    writeln!(
        rs,
        "pub const CREATE_INTERFACE_RVA: usize = {:#x};",
        hex(one("export CreateInterface")?)?
    )
    .unwrap();
    match map.get("interface IClientEngine").map(Vec::as_slice) {
        Some(["version", v]) if v.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_') => {
            writeln!(
                rs,
                "pub const CLIENT_ENGINE_VERSION: &std::ffi::CStr = c{v:?};"
            )
            .unwrap()
        }
        _ => return Err("missing `interface IClientEngine version`".into()),
    }
    writeln!(
        rs,
        "// IClientEngine: (slot, RVA) in CSteamClient's primary vtable."
    )
    .unwrap();
    for (c, key) in ENGINE {
        let (i, r) = slot(key)?;
        writeln!(rs, "pub const {c}: (usize, usize) = ({i}, {r:#x});").unwrap();
    }
    let vtable = |name: &str| -> Result<usize, String> { hex(one(&format!("vtable {name}"))?) };
    let table = |rs: &mut String,
                 name: &str,
                 methods: &[(&str, &str)],
                 prefix: &str|
     -> Result<(), String> {
        writeln!(rs, "// {name}: (slot, RVA).").unwrap();
        for (c, m) in methods {
            let (i, r) = slot(&format!("slot {name} {m}"))?;
            writeln!(rs, "pub const {prefix}{c}: (usize, usize) = ({i}, {r:#x});").unwrap();
        }
        Ok(())
    };
    writeln!(
        rs,
        "pub const USER_PROXY_VTABLE: usize = {:#x};",
        vtable("IClientUserMap")?
    )
    .unwrap();
    table(&mut rs, "IClientUserMap", USER, "")?;
    // The CUser table: all entries or none, with the same slots as the proxy.
    let local: Result<Vec<(usize, usize)>, String> = USER
        .iter()
        .map(|(_, m)| slot(&format!("slot IClientUser.CUser {m}")))
        .collect();
    match local {
        Ok(local) => {
            for ((c, m), (i, _)) in USER.iter().zip(&local) {
                if slot(&format!("slot IClientUserMap {m}"))?.0 != *i {
                    return Err(format!("{c}: CUser and proxy slots differ"));
                }
            }
            let rvas: Vec<String> = local.iter().map(|(_, r)| format!("{r:#x}")).collect();
            writeln!(
                rs,
                "/// CUser's IClientUser RVAs, in the order of USER_PROXY_SLOTS."
            )
            .unwrap();
            writeln!(
                rs,
                "pub const USER_LOCAL_RVAS: Option<[usize; {}]> = Some([{}]);",
                USER.len(),
                rvas.join(", ")
            )
            .unwrap();
        }
        Err(_) => writeln!(
            rs,
            "pub const USER_LOCAL_RVAS: Option<[usize; {}]> = None;",
            USER.len()
        )
        .unwrap(),
    }
    let names: Vec<&str> = USER.iter().map(|(c, _)| *c).collect();
    writeln!(
        rs,
        "pub const USER_PROXY_SLOTS: [(usize, usize); {}] = [{}];",
        USER.len(),
        names.join(", ")
    )
    .unwrap();
    writeln!(
        rs,
        "pub const REMOTE_STORAGE_PROXY_VTABLE: usize = {:#x};",
        vtable("IClientRemoteStorageMap")?
    )
    .unwrap();
    table(&mut rs, "IClientRemoteStorageMap", REMOTE_STORAGE, "")?;
    writeln!(
        rs,
        "pub const APP_MANAGER_PROXY_VTABLE: usize = {:#x};",
        vtable("IClientAppManagerMap")?
    )
    .unwrap();
    table(&mut rs, "IClientAppManagerMap", APP_MANAGER, "")?;
    writeln!(
        rs,
        "pub const COMPAT_PROXY_VTABLE: usize = {:#x};",
        vtable("IClientCompatMap")?
    )
    .unwrap();
    table(&mut rs, "IClientCompatMap", COMPAT, "")?;
    // The host exports `kill` for the engine's kill@plt; the map must show that call.
    match map.get("import kill").map(Vec::as_slice) {
        Some(["plt", _]) => {}
        _ => {
            return Err(
                "missing `import kill plt`: the engine may not call kill through its PLT".into(),
            )
        }
    }
    Ok(rs)
}

/// The constants of a host built without a map. Every address is 0; the host
/// checks ENGINE_MAP_PRESENT before it opens the engine.
fn missing() -> String {
    let mut rs = String::new();
    writeln!(
        rs,
        "// Generated by build.rs from the empty public map; do not edit."
    )
    .unwrap();
    writeln!(rs, "pub const ENGINE_MAP_PRESENT: bool = false;").unwrap();
    writeln!(rs, "pub const ENGINE_SHA256: &str = \"\";").unwrap();
    writeln!(rs, "pub const ENGINE_CLIENT_VERSION: &str = \"\";").unwrap();
    writeln!(rs, "pub const CREATE_INTERFACE_RVA: usize = 0;").unwrap();
    writeln!(
        rs,
        "pub const CLIENT_ENGINE_VERSION: &std::ffi::CStr = c\"\";"
    )
    .unwrap();
    for (c, _) in ENGINE
        .iter()
        .chain(USER)
        .chain(REMOTE_STORAGE)
        .chain(APP_MANAGER)
        .chain(COMPAT)
    {
        writeln!(rs, "pub const {c}: (usize, usize) = (0, 0);").unwrap();
    }
    for v in [
        "USER_PROXY_VTABLE",
        "REMOTE_STORAGE_PROXY_VTABLE",
        "APP_MANAGER_PROXY_VTABLE",
        "COMPAT_PROXY_VTABLE",
    ] {
        writeln!(rs, "pub const {v}: usize = 0;").unwrap();
    }
    writeln!(
        rs,
        "pub const USER_LOCAL_RVAS: Option<[usize; {}]> = None;",
        USER.len()
    )
    .unwrap();
    let names: Vec<&str> = USER.iter().map(|(c, _)| *c).collect();
    writeln!(
        rs,
        "pub const USER_PROXY_SLOTS: [(usize, usize); {}] = [{}];",
        USER.len(),
        names.join(", ")
    )
    .unwrap();
    rs
}
