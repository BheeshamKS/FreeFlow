---
name: banana
description: UI component generation, visual assets, and design system integration using Banana and Gemini image models
---

# Banana - UI Component Generation & Visual Assets

## Purpose
Design, generate, and integrate sleek visual UI components, app icons, theme graphics, and visual design systems directly into your application codebase using the Banana MCP server and generative UI models.

## Usage
```bash
/banana [prompt] [--type icon|banner|component|theme] [--aspect 1:1|16:9|4:3] [--resolution 1K|2K]
```

## Capabilities
- Generate vector and raster UI icons, badges, and status pills
- Build modern theme palettes and design system color tokens
- Create hero banners, splash screens, and desktop overlay graphics
- Iteratively edit existing visual assets with context-aware styling ("dark glass", "acrylic", "neon glow")

## MCP Server Integration
- **Server**: `banana` (`nano-banana-2-mcp`)
- **Tools**: `generate_image`, `edit_image`, `compose_images`
