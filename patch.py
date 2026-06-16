#!/usr/bin/env python3
"""
Usage: python3 patch.py < app.py > app_patched.py
Applies all Menawar dashboard patches:
- Removes night mode (inject_css, _is_night_mode, _theme, sidebar section)
- Expands x-axis to full 24h on all battery/SOC charts
"""
import re, sys

src = sys.stdin.read()

# 1. inject_css signature
src = src.replace(
    "def inject_css(night_mode: bool = False) -> None:",
    "def inject_css() -> None:"
)

# 2. Remove night palette block (keep day palette)
src = re.sub(
    r"    if night_mode:\n        # \u2550\u2550 NIGHT MODE PALETTE \u2550\u2550\n.*?    else:\n        # \u2550\u2550 DAY / PRODUCTION MODE PALETTE \u2550\u2550\n",
    "    # \u2550\u2550 PRODUCTION MODE PALETTE (\u062f\u0627\u0626\u0645\u0627\u064b) \u2550\u2550\n",
    src, flags=re.DOTALL
)

# 3. Remove _is_night_mode() function
src = re.sub(
    r"\ndef _is_night_mode\(\) -> bool:\n.*?\n(?=\ndef _theme)",
    "\n", src, flags=re.DOTALL
)

# 4. Simplify _theme() - always day colors
src = re.sub(
    r"def _theme\(\):.*?(?=\ndef light_layout)",
    'def _theme():\n    return {"grid": "rgba(58,125,30,0.09)", "font": "#2d5a1a"}\n\n',
    src, flags=re.DOTALL
)

# 5. Remove night_mode block in render() + fix inject_css call
src = re.sub(
    r"        # \u2500\u2500 Determine night mode.*?inject_css\(night_mode=night_mode\)",
    "        inject_css()",
    src, flags=re.DOTALL
)

# 6. Remove DISPLAY MODE sidebar section
src = re.sub(
    r'        st\.sidebar\.markdown\("## \U0001f319 DISPLAY MODE"\).*?unsafe_allow_html=True,\n        \)\n\n        st\.sidebar\.markdown\("---"\)\n        is_night_now',
    '        st.sidebar.markdown("---")\n        is_night_now',
    src, flags=re.DOTALL
)

# 7. Battery panel: remove range restriction + full 24h tickvals
src = src.replace(
    '                    range=["06:00", "20:00"],\n'
    '                    tickfont=dict(color=_theme()["font"], size=9),\n'
    '                    tickmode="array",\n'
    '                    tickvals=[f"{h:02d}:{m:02d}" for h in range(6, 21) for m in (0, 30) if not (h == 20 and m == 30)],\n'
    '                    ticktext=[f"{h:02d}:{m:02d}" for h in range(6, 21) for m in (0, 30) if not (h == 20 and m == 30)],',
    '                    tickfont=dict(color=_theme()["font"], size=9),\n'
    '                    tickmode="array",\n'
    '                    tickvals=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],\n'
    '                    ticktext=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],'
)

# 8. _battery_compact: full 24h tickvals
src = src.replace(
    '                tickvals=[f"{h:02d}:{m:02d}" for h in range(6, 21) for m in (0, 30) if not (h == 20 and m == 30)],\n'
    '                ticktext=[f"{h:02d}:{m:02d}" for h in range(6, 21) for m in (0, 30) if not (h == 20 and m == 30)],',
    '                tickvals=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],\n'
    '                ticktext=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],'
)

# 9. Day report x_range full day
src = src.replace(
    '            x_range = ["06:00", "20:00"]',
    '            x_range = ["00:00", "23:30"]'
)

sys.stdout.write(src)
