# DIVI Button Attributes Reference

## Button attributes

| Attribute                              | Purpose                | Example                                    |
| -------------------------------------- | ---------------------- | ------------------------------------------ |
| `custom_button`                        | Enables custom styling | `"on"`                                     |
| `button_text_color`                    | Text color             | `"#ffffff"`                                |
| `button_bg_color`                      | Background             | `"#e2001a"` or `"gcid-primary-color"`      |
| `button_border_radius`                 | Roundness              | `"100px"` (pill)                           |
| `button_border_width`                  | Border                 | `"0px"`                                    |
| `button_text_size`                     | Font size              | `"15px"`                                   |
| `button_font`                          | Font stack + style     | `"\|700\|\|on\|\|\|\|\|"` (bold+uppercase) |
| `button_letter_spacing`                | Spacing                | `"2px"`                                    |
| `button_letter_spacing__hover`         | Hover spacing          | `"2px"`                                    |
| `button_letter_spacing__hover_enabled` | Enable hover override  | `"on"`                                     |
| `custom_padding`                       | Padding (T\|R\|B\|L)   | `"14px\|40px\|14px\|40px\|true\|true"`     |
| `box_shadow_style`                     | Shadow preset          | `"preset1"`                                |
| `box_shadow_vertical`                  | Shadow Y offset        | `"6px"`                                    |
| `box_shadow_blur`                      | Shadow blur            | `"20px"`                                   |
| `box_shadow_color`                     | Shadow color           | `"rgba(226,0,26,0.32)"`                    |

## `button_font` field legend

DIVI stores this as an 8-field pipe-delimited string: `family|weight|style|uppercase|underline|strike|color|line_height`.

- An empty `family` means "inherit theme default" and is usually what you want.
- `weight` is a numeric CSS weight (`400`, `700`).
- `style` is `on` for italic.
- `uppercase` is `on` to force caps.
- Leaving the trailing fields empty is fine.
- The same format applies to `body_font`, `header_font`, etc.

## Critical DIVI quirks

### Hover state uses double-underscore

DIVI uses double-underscore `__hover` for hover state values:

- `button_letter_spacing__hover="2px"`
- `button_letter_spacing__hover_enabled="on"`

The single-underscore variant `button_letter_spacing_hover` exists but is a legacy/unused field. Setting it has no effect. Always use `__hover`.

If you change a base style property (e.g. `button_letter_spacing`) without also updating `button_X__hover`, the style reverts on hover.

### `custom_button="on"` is required

DIVI ignores all custom button style attributes unless `custom_button="on"` is present. If a button doesn't appear styled despite having color/radius attributes, this is almost always the cause.

### Global colors

- `gcid-primary-color` is a token, not a hex value. It resolves to whatever is set in DIVI Theme Options → General → Colors. Prefer it for brand-colored elements so they update automatically if the palette changes.
- Hardcoded hex values (like `#e2001a`) override the global token. Use hardcoded hex only when a specific element intentionally deviates from the brand color.

## Regex safety

Inside the opening tag of a shortcode (`[et_pb_button ...]`), attribute values are quoted and never contain a literal `]`, so `\[et_pb_button [^\]]*\]` safely matches only the opening tag.

This rule applies only to the opening tag. The **inner HTML** of modules like `et_pb_text` and `et_pb_code` freely contains `]` characters (links, JS, template output). Never try to match a whole module body with `[^\]]*`. For bodies, use a non-greedy match against the closing shortcode: `\[et_pb_text [^\]]*\](.*?)\[/et_pb_text\]` with `re.DOTALL`.

`et_pb_code` modules can contain raw HTML and JavaScript — treat them as opaque. Don't touch them unless the user specifically asks.
