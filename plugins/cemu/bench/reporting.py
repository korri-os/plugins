"""A failed run has no performance result, even if raw Present events exist."""


def gate_section(timings: dict[str, float | None]) -> list[str]:
    lines = ["## Gameplay gate", "", "Offsets are seconds after launch starts."]
    for name, key in (
        ("title", "titleAt"),
        ("loading", "loadingAt"),
        ("gameplay", "gameplayAt"),
        ("end gameplay", "endGameplayAt"),
    ):
        value = timings.get(key)
        lines.append(f"- {name} at: {value if value is not None else 'not observed'}")
    return lines + [""]


def not_measured_report(
    reason: str, timings: dict[str, float | None], safety: str
) -> str:
    return "\n".join(
        [
            "# Bench run",
            "",
            "Status: not measured",
            "",
            f"Reason: {reason}",
            "",
            *gate_section(timings),
            "## Save safety",
            "",
            safety,
            "",
            "Raw diagnostic events, if present, are not a measurement.",
            "",
        ]
    )


def fps_section(error: str, stats: dict[str, float]) -> list[str]:
    if error:
        return []
    return [
        "## FPS",
        "",
        "Source: one-second X11 Present Pixmap completion bins; Skip excluded.",
        "Game presentations to Gamescope, not compositor refresh or simulation rate.",
        "p10/p1 use nearest rank; zero bins included.",
        "",
        "| median | p10 | p1 | min |",
        "|---:|---:|---:|---:|",
        f"| {stats['median']:.2f} | {stats['p10']:.2f} | {stats['p1']:.2f} | {stats['min']:.2f} |",
        "",
    ]
