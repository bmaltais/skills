//! Run one command in a herdr pane and print its tail and exit status.
//!
//! The pane is created next to the current one on first use and reused after;
//! its id is kept in `~/.cache/herdr-run/<tab>`, and replaced when the pane is gone.

use serde_json::Value;
use std::process::{Command, exit};
use std::time::{SystemTime, UNIX_EPOCH};

const HELP: &str = "herdr-run [--timeout MS] [--lines N] [--fresh] COMMAND

Runs COMMAND (a shell string) in a reused herdr pane, waits for it, prints the
last N lines (default 40) and `exit=<code>`. Exits with the command's status;
124 on timeout (the command keeps running in the pane, which is printed).
--fresh opens a new pane instead of reusing the remembered one.
Needs HERDR_ENV=1.";

fn herdr(args: &[&str]) -> Option<Value> {
    let out = Command::new("herdr").args(args).output().ok()?;
    if !out.status.success() {
        return None;
    }
    serde_json::from_slice(&out.stdout).ok()
}

fn die(msg: &str) -> ! {
    eprintln!("herdr-run: {msg}");
    exit(2)
}

fn state_file() -> std::path::PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| die("HOME is not set"));
    let tab = std::env::var("HERDR_TAB_ID").unwrap_or_default().replace([':', '/'], "_");
    let dir = std::path::Path::new(&home).join(".cache/herdr-run");
    std::fs::create_dir_all(&dir).unwrap_or_else(|e| die(&format!("cache dir: {e}")));
    dir.join(tab)
}

fn pane(fresh: bool) -> String {
    let file = state_file();
    if !fresh
        && let Ok(id) = std::fs::read_to_string(&file)
        && Command::new("herdr").args(["pane", "get", id.trim()]).output().is_ok_and(|o| o.status.success())
    {
        return id.trim().to_string();
    }
    let split = herdr(&["pane", "split", "--current", "--direction", "right"])
        .unwrap_or_else(|| die("could not split a pane"));
    let id = split["result"]["pane"]["pane_id"]
        .as_str()
        .unwrap_or_else(|| die("split returned no pane id"))
        .to_string();
    let _ = std::fs::write(&file, &id);
    id
}

fn main() {
    if std::env::var("HERDR_ENV").as_deref() != Ok("1") {
        die("not inside herdr (HERDR_ENV is not 1)");
    }
    let (mut timeout, mut lines, mut fresh, mut command) = (600_000u64, 40usize, false, None);
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--help" | "-h" => {
                println!("{HELP}");
                return;
            }
            "--timeout" => timeout = args.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| die("--timeout needs milliseconds")),
            "--lines" => lines = args.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| die("--lines needs a number")),
            "--fresh" => fresh = true,
            _ if command.is_none() => command = Some(a),
            _ => die("one COMMAND string only; quote it"),
        }
    }
    let command = command.unwrap_or_else(|| die(HELP));
    let id = pane(fresh);
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).map_or(0, |d| d.as_nanos());
    let marker = format!("DONE_{}_{}", std::process::id(), nanos % 1_000_000_000);
    let line = format!("{command}; echo {marker}_$?");
    let started = Command::new("herdr").args(["pane", "run", &id, &line]).output();
    if !started.is_ok_and(|o| o.status.success()) {
        die("could not run in the pane");
    }
    let regex = format!("{marker}_[0-9]+");
    let waited = Command::new("herdr")
        .args(["pane", "wait-output", &id, "--regex", &regex, "--timeout", &timeout.to_string()])
        .output()
        .unwrap_or_else(|e| die(&format!("wait: {e}")));
    let text = serde_json::from_slice::<Value>(&waited.stdout)
        .ok()
        .and_then(|v| v["result"]["read"]["text"].as_str().map(String::from))
        .unwrap_or_default();
    // The echoed command line also holds the marker, followed by `$?`, never digits.
    let done = text
        .lines()
        .rev()
        .find_map(|l| l.trim().strip_prefix(&format!("{marker}_")).and_then(|c| c.parse::<i32>().ok()));
    let Some(code) = done else {
        println!("timeout after {timeout} ms; still running in pane {id}");
        exit(124);
    };
    // Output starts after the echoed command line and stops at the marker line.
    let all: Vec<&str> = text.lines().collect();
    let start = all.iter().rposition(|l| l.contains(&format!("echo {marker}"))).map_or(0, |i| i + 1);
    let body: Vec<&str> = all[start..].iter().copied().take_while(|l| !l.trim().starts_with(&marker)).collect();
    let from = body.len().saturating_sub(lines);
    for l in &body[from..] {
        println!("{l}");
    }
    println!("exit={code}");
    exit(code.clamp(0, 255));
}
