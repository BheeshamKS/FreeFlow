# FreeFlow Universal Design System

The unified visual design language for **FreeFlow (Desktop)** and **FreeFlow Pocket (Android)**.

Built on an **Inky Obsidian Glass** aesthetic: pitch-black (`#000000`) canvases, subtle hairline boundaries (`#26262E`), electric azure brand accents (`#5AB4FF`), and dynamic acoustic state lighting.

---

## 1. Brand Identity & Official Logo

The official FreeFlow logo mark features three dynamic vertical flow pulses with rounded caps, colored in a vibrant dual-tone gradient from Electric Cyan to Flow Azure:

- **Vector Master**: `assets/logo.svg`
- **Gradient Start**: `#32FFE4` (Electric Cyan)
- **Gradient End**: `#0072DA` (Deep Flow Azure)
- **Transparent Background**: Standardized for seamless integration across light and dark shells, desktop application docks, taskbars, and Android app launchers.

```
       ┌──┐
       │  │           ┌──┐
       │  │           │  │           ┌──┐
       │  │           │  │           │  │
       │  │           │  │           │  │
       └──┘           │  │           │  │
                      └──┘           └──┘
     Pulse 1        Pulse 2        Pulse 3
```

---

## 2. Color Palette Tokens

| Token Name | Hex / RGBA | Role / Usage |
| :--- | :--- | :--- |
| **`DarkBackground`** | `#000000` | Pure pitch-black canvas background; 0% OLED battery burn. |
| **`DarkSurface`** | `#0E0E12` | Obsidian surface elevation: sidebars, navigation bars, headers. |
| **`DarkCard`** | `#18181C` | Elevated cards, list containers, form inputs, dialog bodies. |
| **`DarkCardHover`** | `#222228` | Interactive card hover elevation. |
| **`DarkCardBorder`** | `#26262E` | Subtle 1px hairline border separating cards and structural panels. |
| **`DarkCardBorderHover`** | `#3B3B48` | Interactive focus and hover border highlight. |
| **`PrimaryBlue`** | `#5AB4FF` | FreeFlow Signature Electric Azure; primary buttons, active tabs, focus rings. |
| **`PrimaryBlueGlow`** | `rgba(90, 180, 255, 0.20)` | Diffuse ambient light aura for the Voice Orb and HUD. |
| **`AccentGreen`** | `#00E676` | Active microphone recording, successful injection, online connection. |
| **`AccentViolet`** | `#D500F9` | AI post-processing, Whisper transcription, LLM grammar formatting. |
| **`AccentGold`** | `#FFD600` | Warning badges, rate limits, cooldown notices. |
| **`AccentRed`** | `#FF5252` | Error alerts, failed transcription diagnostics, destructive actions. |
| **`TextPrimary`** | `#FFFFFF` | High-contrast pure white for headings, primary labels, and inputs. |
| **`TextSecondary`** | `#9E9EA8` | Muted secondary text, subheadings, and metadata. |
| **`TextTertiary`** | `#686874` | Subdued helper hints, keycap shortcuts, and status timestamps. |

---

## 3. Typography Hierarchy

### Font Families
- **Display & Interface**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Ubuntu", sans-serif`
- **Monospace (Hotkeys & Code)**: `"JetBrains Mono", "Ubuntu Mono", "Consolas", monospace`

### Type Scale
| Level | Size | Weight | Tracking | Color | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Headline Large** | 24–28px | 600 (SemiBold) | `-0.5px` | `#FFFFFF` | Page titles, hero headers |
| **Headline Medium** | 20–22px | 600 (SemiBold) | `-0.4px` | `#FFFFFF` | Section titles, modal headers |
| **Title Large** | 16–18px | 600 (SemiBold) | `-0.3px` | `#FFFFFF` | Card headers, sidebar brand |
| **Body Large** | 14–15px | 400 (Regular) | `0px` | `#FFFFFF` | Primary text, transcripts |
| **Body Medium** | 12–13px | 400 (Regular) | `0px` | `#9E9EA8` | Descriptions, settings labels |
| **Label Small** | 10–11px | 600 (SemiBold) | `+0.8px` | `#686874` | Section eyebrows (uppercase) |
| **Keycap Mono** | 11–12px | 600 (SemiBold) | `0px` | `#5AB4FF` | Shortcut badges |

---

## 4. Component Styles

### Buttons
- **Primary Action**: Electric Azure `#5AB4FF` fill with crisp `#000000` text, 8px radius. Hover brightens to `#7EC5FF`.
- **Secondary / Ghost**: Obsidian card `#18181C` fill with `#26262E` hairline border and `#FFFFFF` text. Hover shifts to `#222228` and border `#3B3B48`.
- **Active Recording**: Deep emerald `#062B1F` fill with `#00E676` border and `#A7F3D0` text.
- **Error / Solutions**: Crimson `#2B0F13` fill with `#FF5252` border and `#FECACA` text.

### Inputs & Selectors
- Background: `#18181C`
- Border: `1px solid #26262E`
- Focused: `1px solid #5AB4FF` with `#1C1C22` background
- Text: `#FFFFFF`
- Placeholder: `#686874`

### Voice Orb
- **Idle / Ready**: Electric Azure aura (`#5AB4FF`), inky obsidian core (`#18181C` to `#0E0E12`), glowing cyan-blue mic glyph.
- **Recording**: Active emerald aura (`#00E676`) with harmonic amplitude pulsing and white mic glyph.
- **Transcribing / Polishing**: Vivid violet aura (`#D500F9`) with rhythmic breathing.
- **Error**: Crimson aura (`#FF5252`) with interactive retry pill.

---

## 5. Cross-Platform Parity

FreeFlow maintains identical design tokens, colors, and visual rhythm across:
- **FreeFlow (Desktop)**: Linux (X11 & Wayland), Windows 10/11, macOS
- **FreeFlow Pocket (Android)**: Jetpack Compose Material 3 theme (`Color.kt`, `Theme.kt`, `Type.kt`)
